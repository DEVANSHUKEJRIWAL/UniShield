"""Core orchestrator — OpenClaw-based agent coordination."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime

from openclaw_sdk import OpenClawClient
from openclaw_sdk.core.config import ClientConfig

from unishield.agents.scr.schemas.input_schema import SCRAgentInput, ScanMode, TriggerSource as SCRTrigger
from unishield.agents.scr.scr_runner import SCRRunner, normalize_agent_key
from unishield.config.settings import Settings, settings
from unishield.infrastructure.kafka_client import KafkaProducer
from unishield.memory.shared_memory import AgentOutputNotReady, SharedMemoryClient
from unishield.orchestrator.decision_engine import DecisionEngine
from unishield.orchestrator.finalizer import WorkflowFinalizer
from unishield.orchestrator.workflow_definitions import WORKFLOW_DEFINITIONS
from unishield.orchestrator.workflow_state import WorkflowState, WorkflowStateStore
from unishield.schemas.workflow_schemas import TriggerSource, WorkflowTrigger

logger = logging.getLogger(__name__)

FIXED_SOURCES = {TriggerSource.MANUAL_FRONTEND, TriggerSource.SCHEDULED, TriggerSource.CICD}
DYNAMIC_SOURCES = {TriggerSource.INCIDENT, TriggerSource.ALERT_ESCALATION, TriggerSource.THREAT_ACTOR}


class Orchestrator:
    """Manages workflow execution via OpenClaw SDK."""

    def __init__(
        self,
        openclaw_config: ClientConfig,
        shared_memory: SharedMemoryClient,
        state_store: WorkflowStateStore,
        decision_engine: DecisionEngine,
        finalizer: WorkflowFinalizer,
        kafka: KafkaProducer,
        app_settings: Settings | None = None,
        scr_runner: SCRRunner | None = None,
    ) -> None:
        self.openclaw_config = openclaw_config
        self.shared_memory = shared_memory
        self.state_store = state_store
        self.decision_engine = decision_engine
        self.finalizer = finalizer
        self.kafka = kafka
        self.settings = app_settings or settings
        self.scr_runner = scr_runner
        self._trigger_log: list[tuple[str, str, str]] = []
        self._executing: set[str] = set()

    SCR_REQUIRED_WORKFLOWS = frozenset({"code-review-only", "compliance-readiness", "full-security-audit"})

    @property
    def trigger_log(self) -> list[tuple[str, str, str]]:
        return self._trigger_log

    async def start_workflow(self, trigger: WorkflowTrigger, *, run_inline: bool = True) -> str:
        workflow_id = f"WF-{uuid.uuid4().hex[:8]}"
        flow_type = "dynamic" if trigger.source in DYNAMIC_SOURCES else "fixed"
        definition = WORKFLOW_DEFINITIONS.get(trigger.workflow_name, {})
        steps = definition.get("steps", [])
        agent_states = {
            normalize_agent_key(agent): "PENDING" for step in steps for agent in step
        }

        state = WorkflowState(
            workflow_id=workflow_id,
            client_id=trigger.client_id,
            incident_id=trigger.incident_id,
            workflow_name=trigger.workflow_name,
            flow_type=flow_type,
            triggered_by=trigger.source.value,
            started_at=datetime.now(UTC),
            agent_states=agent_states,
            current_step_index=0,
            max_retries=self.settings.max_agent_retries,
            context={
                "repo_url": trigger.repo_url,
                "repo_ref": trigger.repo_ref,
                "correlation_id": trigger.correlation_id or workflow_id,
                **trigger.context,
            },
        )
        await self.state_store.save(state)

        await self.kafka.publish(
            "workflow.started",
            {
                "workflow_id": workflow_id,
                "client_id": trigger.client_id,
                "workflow_name": trigger.workflow_name,
                "flow_type": flow_type,
            },
            key=workflow_id,
        )

        if run_inline:
            await self.execute_workflow(workflow_id)

        return workflow_id

    async def execute_workflow(self, workflow_id: str) -> None:
        """Run workflow agents after the workflow record has been created."""
        if workflow_id in self._executing:
            logger.warning("Workflow %s is already executing — skipping duplicate run", workflow_id)
            return

        self._executing.add(workflow_id)
        try:
            state = await self.state_store.load(workflow_id)
            if not state:
                logger.error("Cannot execute unknown workflow %s", workflow_id)
                return

            definition = WORKFLOW_DEFINITIONS.get(state.workflow_name, {})
            steps = definition.get("steps", [])

            try:
                if state.flow_type == "fixed" and steps:
                    await self._trigger_agents(steps[0], state)
                elif state.flow_type == "dynamic":
                    await self._trigger_agents(["unishield-web"], state)
            except Exception as exc:
                logger.exception("Workflow %s execution failed", workflow_id)
                await self.state_store.fail(workflow_id, str(exc))
                raise
        finally:
            self._executing.discard(workflow_id)

    async def on_agent_complete(self, event: dict) -> None:
        workflow_id = event["workflow_id"]
        raw_agent = event.get("agent_id", "")
        completed_agent = normalize_agent_key(raw_agent)

        state = await self.state_store.load(workflow_id)
        if not state:
            return

        await self.state_store.mark_agent_done(workflow_id, completed_agent)
        state = await self.state_store.load(workflow_id)
        if not state:
            return

        try:
            surface = await self.shared_memory.read_decision_surface(workflow_id, completed_agent)
        except Exception:
            logger.warning("Decision surface not ready for %s", completed_agent)
            return

        if state.flow_type == "fixed" and not state.escalated_to_dynamic:
            if self.decision_engine.should_escalate(completed_agent, surface, state):
                await self._escalate_to_dynamic(state, surface)
                state = await self.state_store.load(workflow_id)
                if not state:
                    return

            if (
                state.workflow_name in self.SCR_REQUIRED_WORKFLOWS
                and completed_agent == "scr"
                and state.current_step_index == 0
            ):
                try:
                    scr_output = await self.shared_memory.read_agent_output(workflow_id, "scr")
                except AgentOutputNotReady:
                    logger.error("SCR finished without shared-memory output for workflow %s", workflow_id)
                    await self.state_store.fail(workflow_id, "SCR output missing")
                    await self._finalize(state)
                    return
                if scr_output.get("scan_status") == "FAILED":
                    await self.state_store.fail(
                        workflow_id,
                        scr_output.get("error_message") or "SCR scan failed",
                    )
                    await self._finalize(state)
                    return

            next_agents = await self._get_next_fixed_step(state, completed_agent)
        else:
            next_agents = self.decision_engine.evaluate(state, completed_agent, surface)

        if state.context.get("pending_pause"):
            reason = state.context.pop("pending_pause")
            await self._handle_human_gate(state, reason)
            if next_agents:
                await self._trigger_agents(next_agents, state)
            return

        if not next_agents:
            if completed_agent == "reporting" and surface.requires_human_approval:
                await self._handle_human_gate(state, "Requires human approval")
            else:
                await self._finalize(state)
            return

        await self._trigger_agents(next_agents, state)

    async def _trigger_agents(self, agent_ids: list[str], state: WorkflowState) -> None:
        async with OpenClawClient.connect(
            gateway_ws_url=self.openclaw_config.gateway_ws_url,
            api_key=self.openclaw_config.api_key,
            mock_mode=self.openclaw_config.mock_mode,
        ) as client:
            tasks = []
            for agent_id in agent_ids:
                key = normalize_agent_key(agent_id)
                await self.state_store.mark_agent_running(state.workflow_id, key)
                self._trigger_log.append((state.workflow_id, agent_id, "NORMAL"))
                payload = self._build_agent_payload(agent_id, state)

                if key == "scr" and self.scr_runner:
                    tasks.append(self._run_scr(state, payload))
                else:
                    agent = client.get_agent(agent_id, session_name=state.workflow_id)
                    tasks.append(agent.execute(json.dumps(payload)))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            step_failed = False
            for agent_id, result in zip(agent_ids, results):
                if isinstance(result, Exception):
                    step_failed = True
                    await self.state_store.mark_agent_failed(
                        state.workflow_id, normalize_agent_key(agent_id)
                    )
                    logger.error("Agent %s failed: %s", agent_id, result)
                else:
                    await self._notify_agent_complete(agent_id, state)

            if step_failed:
                await self.state_store.fail(state.workflow_id, "Agent step failed")
                failed_state = await self.state_store.load(state.workflow_id)
                if failed_state:
                    await self._finalize(failed_state)
                return

    async def _notify_agent_complete(self, agent_id: str, state: WorkflowState) -> None:
        """Advance workflow after an agent task finishes (inline path for local dev)."""
        key = normalize_agent_key(agent_id)
        if key == "scr":
            try:
                await self.shared_memory.read_agent_output(state.workflow_id, "scr")
            except AgentOutputNotReady:
                logger.error(
                    "SCR task completed but shared-memory output is missing for workflow %s",
                    state.workflow_id,
                )
                await self.state_store.mark_agent_failed(state.workflow_id, "scr")
                return
        else:
            try:
                await self.shared_memory.read_decision_surface(state.workflow_id, key)
            except AgentOutputNotReady:
                await self.shared_memory.write_agent_output(
                    state.workflow_id,
                    key,
                    {
                        "agent_id": key,
                        "completed_at": datetime.now(UTC).isoformat(),
                        "risk_score": 10,
                        "highest_severity": "LOW",
                        "requires_human_approval": False,
                        "auto_remediation_safe": True,
                        "forward_to": [],
                        "critical_count": 0,
                        "secret_findings_count": 0,
                        "correlated_to_incident": False,
                    },
                )
        await self.on_agent_complete(
            {"workflow_id": state.workflow_id, "agent_id": agent_id}
        )

    async def _run_scr(self, state: WorkflowState, payload: dict) -> None:
        if not self.scr_runner:
            raise RuntimeError("SCR runner is not configured on the orchestrator")
        await self.shared_memory.write_agent_output(
            state.workflow_id,
            "scr",
            {
                "agent_id": "scr",
                "completed_at": datetime.now(UTC).isoformat(),
                "scan_status": "RUNNING",
                "risk_score": 0,
                "highest_severity": "LOW",
                "requires_human_approval": False,
                "auto_remediation_safe": True,
                "forward_to": [],
                "critical_count": 0,
                "secret_findings_count": 0,
                "correlated_to_incident": False,
                "files_discovered": 0,
                "top_findings": [],
                "attack_paths_summary": {
                    "total_paths": 0,
                    "crown_jewel_paths": 0,
                    "top_chokepoint": None,
                    "highest_blast_score": 0,
                },
            },
        )
        ctx = state.context
        scan_mode_raw = payload.get("scan_mode") or ctx.get("scan_mode") or "full_repo"
        scan_mode = ScanMode.FULL_REPO
        if str(scan_mode_raw).lower() == "incremental":
            scan_mode = ScanMode.INCREMENTAL
        scan_input = SCRAgentInput(
            request_id=payload.get("request_id", str(uuid.uuid4())),
            client_id=state.client_id,
            workflow_id=state.workflow_id,
            triggered_by=SCRTrigger.MANUAL,
            scan_mode=scan_mode,
            repo_url=payload.get("repo_url"),
            repo_ref=payload.get("repo_ref"),
            repo_auth_token=payload.get("repo_auth_token"),
            file_paths=payload.get("file_paths", []),
            diff_base=payload.get("diff_base"),
            diff_head=payload.get("diff_head"),
            exclude_patterns=payload.get("exclude_patterns") or [],
            crown_jewels=payload.get("crown_jewels") or [],
            correlation_id=state.context.get("correlation_id"),
            connection_id=payload.get("connection_id") or ctx.get("connection_id"),
        )
        await self.scr_runner.run(scan_input)

    async def _get_next_fixed_step(self, state: WorkflowState, completed_agent: str) -> list[str]:
        plan = WORKFLOW_DEFINITIONS.get(state.workflow_name, {})
        steps = plan.get("steps", [])
        if not steps:
            return []

        current = steps[state.current_step_index]
        pending = [
            normalize_agent_key(a)
            for a in current
            if state.agent_states.get(normalize_agent_key(a)) not in ("DONE", "FAILED")
        ]
        if pending:
            return []

        next_idx = state.current_step_index + 1
        if next_idx >= len(steps):
            return []
        state.current_step_index = next_idx
        await self.state_store.save(state)
        return steps[next_idx]

    async def _escalate_to_dynamic(self, state: WorkflowState, surface) -> None:
        await self.state_store.escalate_to_dynamic(state.workflow_id)

    async def _handle_human_gate(self, state: WorkflowState, reason: str) -> None:
        await self.state_store.pause(
            state.workflow_id, reason, self.settings.human_gate_timeout_hours
        )
        await self.kafka.publish(
            "workflow.human_gate",
            {"workflow_id": state.workflow_id, "client_id": state.client_id, "reason": reason},
            key=state.workflow_id,
        )

    async def approve_workflow(self, workflow_id: str, approved_by: str) -> None:
        await self.state_store.resume(workflow_id, approved_by)
        state = await self.state_store.load(workflow_id)
        if state:
            await self._finalize(state)

    async def _finalize(self, state: WorkflowState) -> None:
        try:
            await self.finalizer.finalize(state.workflow_id, state.client_id)
        except Exception as exc:
            logger.exception("Workflow %s finalization failed", state.workflow_id)
            await self.state_store.fail(state.workflow_id, str(exc))
            raise

    def _build_agent_payload(self, agent_id: str, state: WorkflowState) -> dict:
        ctx = state.context
        base = {
            "workflow_id": state.workflow_id,
            "client_id": state.client_id,
            "request_id": str(uuid.uuid4()),
            "repo_url": ctx.get("repo_url") or state.context.get("repo_url"),
            "repo_ref": ctx.get("repo_ref") or state.context.get("repo_ref"),
        }
        if normalize_agent_key(agent_id) == "scr":
            base.update(
                {
                    "file_paths": ctx.get("file_paths", []),
                    "repo_auth_token": ctx.get("repo_auth_token"),
                    "exclude_patterns": ctx.get("exclude_patterns", []),
                    "crown_jewels": ctx.get("crown_jewels", []),
                    "scan_mode": ctx.get("scan_mode"),
                    "diff_base": ctx.get("diff_base"),
                    "diff_head": ctx.get("diff_head"),
                    "connection_id": ctx.get("connection_id"),
                }
            )
        return base
