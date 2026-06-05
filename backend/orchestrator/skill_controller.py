"""Skill-first orchestrator — OpenClaw agent plans, Python tools invoke agents."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from openclaw_sdk import OpenClawClient

from backend.agents.skill_executor import execute_with_skill, parse_json_response
from backend.orchestrator.decision_engine import DecisionEngine
from backend.orchestrator.orchestrator_tools import ORCHESTRATOR_TOOL_CATALOG, OrchestratorToolHost
from backend.orchestrator.routing_rules import ROUTING_RULES
from backend.orchestrator.workflow_definitions import WORKFLOW_DEFINITIONS
from backend.schemas.decision_surface import AgentDecisionSurface
from backend.scr.scr_runner import normalize_agent_key

if TYPE_CHECKING:
    from backend.orchestrator.orchestrator import Orchestrator
    from backend.orchestrator.workflow_state import WorkflowState

logger = logging.getLogger(__name__)


class OrchestratorSkillController:
    """Runs workflow progression via OpenClaw orchestrator skill + tool host."""

    def __init__(self, orchestrator: "Orchestrator") -> None:
        self._orch = orchestrator
        self._decision_engine = orchestrator.decision_engine

    async def run_initial_step(self, state: "WorkflowState") -> None:
        """Start workflow — orchestrator skill decides first agent tool(s)."""
        agents = await self._plan_agents(state, completed_agent=None, surface=None)
        if not agents:
            await self._orch._finalize(state)
            return
        await self._orch._trigger_agents_via_skill(agents, state)

    async def run_after_agent_complete(
        self,
        state: "WorkflowState",
        completed_agent: str,
        surface: AgentDecisionSurface,
    ) -> None:
        """After agent.complete — skill plans next tool invocations."""
        if state.context.get("pending_pause"):
            reason = state.context.pop("pending_pause")
            await self._orch._handle_human_gate(state, reason)

        agents = await self._plan_agents(state, completed_agent=completed_agent, surface=surface)
        if not agents:
            if completed_agent == "reporting" and surface.requires_human_approval:
                await self._orch.finalizer.persist_snapshot(
                    state.workflow_id,
                    state.client_id,
                    workflow_name=state.workflow_name,
                )
                await self._orch._handle_human_gate(state, "Requires human approval")
            else:
                await self._orch._finalize(state)
            return

        if state.paused:
            return
        await self._orch._trigger_agents_via_skill(agents, state)

    async def _plan_agents(
        self,
        state: "WorkflowState",
        *,
        completed_agent: str | None,
        surface: AgentDecisionSurface | None,
    ) -> list[str]:
        if self._orch.openclaw_config.mock_mode or self._orch.settings.orchestrator_skill_scripted:
            return await self._scripted_plan(state, completed_agent, surface)

        return await self._llm_plan(state, completed_agent, surface)

    async def _scripted_plan(
        self,
        state: "WorkflowState",
        completed_agent: str | None,
        surface: AgentDecisionSurface | None,
    ) -> list[str]:
        if completed_agent is None:
            definition = WORKFLOW_DEFINITIONS.get(state.workflow_name, {})
            steps = definition.get("steps", [])
            if state.flow_type == "fixed" and steps:
                return list(steps[0])
            return ["unishield-scr"]

        if state.flow_type == "fixed" and not state.escalated_to_dynamic:
            if surface and self._decision_engine.should_escalate(
                completed_agent, surface, state
            ) and state.workflow_name not in self._orch.SCR_REQUIRED_WORKFLOWS:
                await self._orch._escalate_to_dynamic(state, surface)
                state = await self._orch.state_store.load(state.workflow_id) or state

            if state.flow_type == "fixed" and not state.escalated_to_dynamic:
                return await self._orch._get_next_fixed_step(state, completed_agent)

        if surface is None:
            return []
        return self._decision_engine.evaluate(state, completed_agent, surface)

    async def _llm_plan(
        self,
        state: "WorkflowState",
        completed_agent: str | None,
        surface: AgentDecisionSurface | None,
    ) -> list[str]:
        payload: dict[str, Any] = {
            "workflow_id": state.workflow_id,
            "workflow_name": state.workflow_name,
            "flow_type": state.flow_type,
            "completed_agent": completed_agent,
            "decision_surface": surface.model_dump(mode="json") if surface else None,
            "available_tools": ORCHESTRATOR_TOOL_CATALOG,
            "routing_rules": ROUTING_RULES,
            "workflow_plan": WORKFLOW_DEFINITIONS.get(state.workflow_name),
            "response_schema": {
                "tool_calls": [{"name": "invoke_scr", "args": {}}],
                "next_agents": ["unishield-cma"],
                "complete": False,
            },
        }
        try:
            async with OpenClawClient.connect(
                gateway_ws_url=self._orch.openclaw_config.gateway_ws_url,
                api_key=self._orch.openclaw_config.api_key,
                mock_mode=self._orch.openclaw_config.mock_mode,
            ) as client:
                agent = client.get_agent("unishield-orchestrator", session_name=state.workflow_id)
                result = await execute_with_skill(
                    agent,
                    "unishield-orchestrator",
                    payload,
                    stage="routing" if completed_agent else "workflow_start",
                    output_schema=payload["response_schema"],
                )
                parsed = parse_json_response(result.content or "")
                if parsed:
                    if parsed.get("complete"):
                        return []
                    next_agents = parsed.get("next_agents") or []
                    if next_agents:
                        return [str(a) for a in next_agents]
        except Exception as exc:
            logger.warning("Orchestrator skill plan failed — scripted fallback: %s", exc)

        return await self._scripted_plan(state, completed_agent, surface)

    async def execute_agent_tools(self, agent_ids: list[str], state: "WorkflowState") -> None:
        """Invoke orchestrator tools for each planned agent (parallel when same step)."""

        async def _run_one(agent_id: str) -> None:
            key = normalize_agent_key(agent_id)
            await self._orch.state_store.mark_agent_running(state.workflow_id, key)
            self._orch._trigger_log.append((state.workflow_id, agent_id, "SKILL"))
            host = OrchestratorToolHost(self._orch, state)
            tool_name = OrchestratorToolHost.agent_id_to_tool(agent_id)
            await host.invoke(tool_name)
            if not (key == "scr" and self._orch.settings.scr_via_kafka):
                await self._orch._notify_agent_complete(agent_id, state)

        results = await asyncio.gather(*[_run_one(a) for a in agent_ids], return_exceptions=True)
        for agent_id, result in zip(agent_ids, results):
            if isinstance(result, Exception):
                key = normalize_agent_key(agent_id)
                await self._orch.state_store.mark_agent_failed(state.workflow_id, key)
                raise result
