"""OpenClaw orchestrator skill routing — decide next agents from decision surfaces."""

from __future__ import annotations

import json
import logging
from typing import Any

from openclaw_sdk import OpenClawClient
from openclaw_sdk.core.config import ClientConfig

from backend.agents.skill_executor import execute_with_skill, parse_json_response
from backend.orchestrator.routing_rules import ROUTING_RULES
from backend.orchestrator.workflow_definitions import WORKFLOW_DEFINITIONS
from backend.orchestrator.workflow_state import WorkflowState
from backend.schemas.decision_surface import AgentDecisionSurface

logger = logging.getLogger(__name__)


class SkillRouter:
    """Uses OpenClaw orchestrator agent + ROUTING_RULES to pick next agents."""

    def __init__(self, openclaw_config: ClientConfig) -> None:
        self._config = openclaw_config

    async def next_agents(
        self,
        state: WorkflowState,
        completed_agent: str,
        surface: AgentDecisionSurface,
        *,
        fallback: list[str],
    ) -> list[str]:
        if self._config.mock_mode:
            return fallback

        payload: dict[str, Any] = {
            "workflow_id": state.workflow_id,
            "workflow_name": state.workflow_name,
            "flow_type": state.flow_type,
            "completed_agent": completed_agent,
            "decision_surface": surface.model_dump(mode="json"),
            "routing_rules": [
                {
                    "after": r["after"],
                    "next_agents": r.get("next_agents", []),
                    "priority": r.get("priority"),
                    "reason": r.get("reason"),
                    "pause": r.get("pause", False),
                    "complete": r.get("complete", False),
                }
                for r in ROUTING_RULES
            ],
            "workflow_plan": WORKFLOW_DEFINITIONS.get(state.workflow_name),
            "current_step_index": state.current_step_index,
            "response_schema": {
                "next_agents": ["list of agent ids e.g. unishield-cma"],
                "pause": "boolean",
                "pause_reason": "string or null",
                "complete": "boolean",
            },
        }

        try:
            async with OpenClawClient.connect(
                gateway_ws_url=self._config.gateway_ws_url,
                api_key=self._config.api_key,
                mock_mode=self._config.mock_mode,
            ) as client:
                agent = client.get_agent("unishield-orchestrator", session_name=state.workflow_id)
                result = await execute_with_skill(
                    agent,
                    "unishield-orchestrator",
                    payload,
                    stage="routing",
                    output_schema=payload["response_schema"],
                )
                parsed = parse_json_response(result.content or "")
                if not parsed:
                    logger.warning("Skill router returned non-JSON — using Python fallback")
                    return fallback
                if parsed.get("complete"):
                    return []
                if parsed.get("pause"):
                    state.context["pending_pause"] = parsed.get("pause_reason") or "Skill router pause"
                next_agents = parsed.get("next_agents") or []
                if isinstance(next_agents, list) and next_agents:
                    return [str(a) for a in next_agents]
        except Exception as exc:
            logger.warning("Skill router unavailable — using Python fallback: %s", exc)

        return fallback
