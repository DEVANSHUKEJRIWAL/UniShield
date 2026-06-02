"""Core orchestrator — workflow execution, routing, and agent coordination."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from unishield.config.settings import settings
from unishield.infrastructure.kafka_client import KafkaClient
from unishield.memory.shared_memory import SharedMemoryClient
from unishield.orchestrator.decision_engine import DecisionEngine
from unishield.orchestrator.finalizer import WorkflowFinalizer
from unishield.orchestrator.workflow_definitions import WORKFLOW_DEFINITIONS
from unishield.orchestrator.workflow_state import WorkflowState, WorkflowStateStore
from unishield.schemas.workflow_schemas import AgentCompleteEvent, TriggerSource, WorkflowTrigger

logger = logging.getLogger(__name__)

FIXED_SOURCES = {
    TriggerSource.MANUAL_FRONTEND,
    TriggerSource.SCHEDULED,
    TriggerSource.CICD,
}
DYNAMIC_SOURCES = {
    TriggerSource.INCIDENT,
    TriggerSource.ALERT_ESCALATION,
    TriggerSource.THREAT_ACTOR,
}

AGENT_TOPIC_MAP = {
    "UniShield-SCR": "scr.scan.requests",
    "UniShield-Web": "web.scan.requests",
    "UniShield-AF": "af.scan.requests",
    "UniShield-ASM": "asm.scan.requests",
    "UniShield-CMA": "cma.scan.requests",
    "UniShield-CloudSec": "cloudsec.scan.requests",
    "UniShield-Insider": "insider.scan.requests",
    "UniShield-Reporting": "reporting.scan.requests",
}


class Orchestrator:
    """Manages workflow execution, routing, state, and agent coordination."""

    def __init__(
        self,
        kafka: KafkaClient,
        shared_memory: SharedMemoryClient,
        state_store: WorkflowStateStore,
        decision_engine: DecisionEngine,
        finalizer: WorkflowFinalizer,
    ) -> None:
        self._kafka = kafka
        self._shared_memory = shared_memory
        self._state_store = state_store
        self._decision_engine = decision_engine
        self._finalizer = finalizer
        self._trigger_log: list[tuple[str, str, str]] = []

    @property
    def trigger_log(self) -> list[tuple[str, str, str]]:
        """(workflow_id, agent_id, priority) — for testing."""
        return self._trigger_log

    async def start_workflow(self, trigger: WorkflowTrigger) -> str:
        workflow_id = str(uuid.uuid4())
        flow_type = "dynamic" if trigger.source in DYNAMIC_SOURCES else "fixed"

        definition = WORKFLOW_DEFINITIONS.get(trigger.workflow_name, {})
        steps = definition.get("steps", [])
        first_step = steps[0] if steps else []

        agent_states = {agent: "PENDING" for step in steps for agent in step}

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
            max_retries=settings.max_agent_retries,
            context={
                "repo_url": trigger.repo_url,
                "repo_ref": trigger.repo_ref,
                "correlation_id": trigger.correlation_id or workflow_id,
                **trigger.context,
            },
        )

        await self._state_store.save(state)

        if first_step:
            await self._execute_fixed_step(state, first_step)

        return workflow_id

    async def on_agent_complete(self, event: AgentCompleteEvent) -> None:
        workflow = await self._state_store.load(event.workflow_id)
        if not workflow or workflow.status in ("COMPLETED", "FAILED"):
            return

        if event.status == "FAILED":
            await self._state_store.mark_agent_failed(event.workflow_id, event.agent_id)
            return

        await self._state_store.mark_agent_done(event.workflow_id, event.agent_id)
        workflow = await self._state_store.load(event.workflow_id)
        if not workflow:
            return

        try:
            surface = await self._shared_memory.read_decision_surface(
                event.workflow_id, event.agent_id
            )
        except Exception:
            logger.warning("Decision surface not ready for %s", event.agent_id)
            surface = None

        if surface and not workflow.escalated_to_dynamic:
            if self._decision_engine.should_escalate(event.agent_id, surface, workflow):
                await self._escalate_to_dynamic(
                    workflow, f"Escalated after {event.agent_id} completion"
                )
                workflow = await self._state_store.load(event.workflow_id)
                if not workflow:
                    return

        if workflow.flow_type == "fixed" and not workflow.escalated_to_dynamic:
            await self._advance_fixed_flow(workflow, event.agent_id)
        elif surface:
            await self._advance_dynamic_flow(workflow, event.agent_id, surface)

    async def _advance_fixed_flow(self, workflow: WorkflowState, completed_agent: str) -> None:
        definition = WORKFLOW_DEFINITIONS.get(workflow.workflow_name, {})
        steps = definition.get("steps", [])
        if not steps:
            await self._finalize(workflow)
            return

        current_step = steps[workflow.current_step_index]
        pending_in_step = [
            a for a in current_step if workflow.agent_states.get(a) not in ("DONE", "FAILED")
        ]
        if pending_in_step:
            return

        next_index = workflow.current_step_index + 1
        if next_index >= len(steps):
            await self._finalize(workflow)
            return

        workflow.current_step_index = next_index
        await self._state_store.save(workflow)
        await self._execute_fixed_step(workflow, steps[next_index])

    async def _advance_dynamic_flow(
        self,
        workflow: WorkflowState,
        completed_agent: str,
        surface,
    ) -> None:
        next_agents = self._decision_engine.evaluate(workflow, completed_agent, surface)

        if workflow.context.get("pending_pause"):
            reason = workflow.context.pop("pending_pause")
            await self._handle_human_gate(workflow, reason)
            if next_agents:
                await self._execute_dynamic_step(workflow, next_agents)
            return

        if not next_agents:
            if completed_agent == "UniShield-Reporting" and not surface.requires_human_approval:
                await self._finalize(workflow)
            elif completed_agent == "UniShield-Reporting" and surface.requires_human_approval:
                await self._handle_human_gate(workflow, "Requires human approval")
            else:
                await self._finalize(workflow)
            return

        await self._execute_dynamic_step(workflow, next_agents)

    async def _execute_fixed_step(
        self,
        workflow: WorkflowState,
        step_agents: list[str],
    ) -> None:
        await asyncio.gather(
            *[self._trigger_agent(agent, workflow) for agent in step_agents]
        )

    async def _execute_dynamic_step(
        self,
        workflow: WorkflowState,
        next_agents: list[str],
    ) -> None:
        await asyncio.gather(
            *[self._trigger_agent(agent, workflow) for agent in next_agents]
        )

    async def _escalate_to_dynamic(self, workflow: WorkflowState, reason: str) -> None:
        logger.warning("Escalating workflow %s to dynamic: %s", workflow.workflow_id, reason)
        await self._state_store.escalate_to_dynamic(workflow.workflow_id)
        workflow.escalated_to_dynamic = True
        workflow.flow_type = "dynamic"

    async def _trigger_agent(
        self,
        agent_id: str,
        workflow: WorkflowState,
        priority: str = "NORMAL",
    ) -> None:
        topic = AGENT_TOPIC_MAP.get(agent_id, f"{agent_id.lower()}.scan.requests")
        payload = {
            "workflow_id": workflow.workflow_id,
            "client_id": workflow.client_id,
            "agent_id": agent_id,
            "incident_id": workflow.incident_id,
            "correlation_id": workflow.context.get("correlation_id"),
            "repo_url": workflow.context.get("repo_url"),
            "repo_ref": workflow.context.get("repo_ref"),
            "priority": priority,
        }
        await self._kafka.publish(topic, payload, key=workflow.workflow_id)
        await self._state_store.mark_agent_running(workflow.workflow_id, agent_id)
        self._trigger_log.append((workflow.workflow_id, agent_id, priority))
        logger.info("Triggered %s on topic %s (priority=%s)", agent_id, topic, priority)

    async def _handle_human_gate(self, workflow: WorkflowState, reason: str) -> None:
        await self._state_store.pause(
            workflow.workflow_id,
            reason,
            settings.human_gate_timeout_hours,
        )
        await self._kafka.publish(
            "workflow.human_gate",
            {
                "workflow_id": workflow.workflow_id,
                "client_id": workflow.client_id,
                "reason": reason,
                "status": "PAUSED",
            },
            key=workflow.workflow_id,
        )

    async def approve_workflow(self, workflow_id: str, approved_by: str) -> None:
        await self._state_store.resume(workflow_id, approved_by)
        workflow = await self._state_store.load(workflow_id)
        if not workflow:
            return

        definition = WORKFLOW_DEFINITIONS.get(workflow.workflow_name, {})
        steps = definition.get("steps", [])
        next_index = workflow.current_step_index + 1
        if next_index < len(steps):
            workflow.current_step_index = next_index
            await self._state_store.save(workflow)
            await self._execute_fixed_step(workflow, steps[next_index])
        else:
            await self._finalize(workflow)

    async def _finalize(self, workflow: WorkflowState) -> None:
        await self._finalizer.finalize(workflow.workflow_id, workflow.client_id)
