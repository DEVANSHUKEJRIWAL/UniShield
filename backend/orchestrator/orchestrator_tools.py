"""Orchestrator Python tools — specialist agents invoked by skill session."""

from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING, Any

from backend.scr.schemas.input_schema import SCRAgentInput, ScanMode, TriggerSource as SCRTrigger
from backend.scr.scr_runner import normalize_agent_key

if TYPE_CHECKING:
    from backend.orchestrator.orchestrator import Orchestrator
    from backend.orchestrator.workflow_state import WorkflowState

logger = logging.getLogger(__name__)

ORCHESTRATOR_TOOL_CATALOG = [
    {"name": "invoke_scr", "description": "Run unishield-scr skill agent (full code review pipeline)"},
    {"name": "invoke_cma", "description": "Run unishield-cma compliance mapping"},
    {"name": "invoke_reporting", "description": "Run unishield-reporting executive report"},
    {"name": "invoke_web", "description": "Run unishield-web application security assessment"},
    {"name": "invoke_asm", "description": "Run unishield-asm attack surface mapping"},
    {"name": "invoke_cloudsec", "description": "Run unishield-cloudsec cloud security assessment"},
    {"name": "pause_workflow", "description": "Pause for human approval gate"},
    {"name": "finalize_workflow", "description": "Finalize workflow snapshot to Postgres"},
]


class OrchestratorToolHost:
    """Tools the OpenClaw orchestrator agent calls to run specialist agents."""

    def __init__(self, orchestrator: "Orchestrator", state: "WorkflowState") -> None:
        self._orch = orchestrator
        self._state = state

    def catalog(self) -> list[dict[str, Any]]:
        return ORCHESTRATOR_TOOL_CATALOG

    async def invoke(self, name: str, **kwargs: Any) -> dict[str, Any]:
        handler = getattr(self, f"_{name}", None)
        if not handler:
            raise KeyError(f"Unknown orchestrator tool: {name}")
        logger.info("Orchestrator skill tool: %s workflow=%s", name, self._state.workflow_id)
        return await handler(**kwargs)

    async def _invoke_scr(self, **kwargs: Any) -> dict[str, Any]:
        if self._orch.settings.scr_via_kafka:
            payload = self._orch._build_agent_payload("unishield-scr", self._state)
            payload.update(kwargs)
            await self._orch._publish_scr_execute(self._state, payload)
            return {"agent_id": "unishield-scr", "status": "published"}
        payload = self._orch._build_agent_payload("unishield-scr", self._state)
        payload.update(kwargs)
        await self._orch._run_scr(self._state, payload)
        return {"agent_id": "unishield-scr", "status": "completed"}

    async def _invoke_cma(self, **kwargs: Any) -> dict[str, Any]:
        await self._orch._run_cma(self._state)
        return {"agent_id": "unishield-cma", "status": "completed"}

    async def _invoke_reporting(self, **kwargs: Any) -> dict[str, Any]:
        await self._orch._run_reporting(self._state)
        return {"agent_id": "unishield-reporting", "status": "completed"}

    async def _invoke_web(self, **kwargs: Any) -> dict[str, Any]:
        await self._orch._run_dynamic_agent("web", self._state)
        return {"agent_id": "unishield-web", "status": "completed"}

    async def _invoke_asm(self, **kwargs: Any) -> dict[str, Any]:
        await self._orch._run_dynamic_agent("asm", self._state)
        return {"agent_id": "unishield-asm", "status": "completed"}

    async def _invoke_cloudsec(self, **kwargs: Any) -> dict[str, Any]:
        await self._orch._run_dynamic_agent("cloudsec", self._state)
        return {"agent_id": "unishield-cloudsec", "status": "completed"}

    async def _pause_workflow(self, reason: str = "Requires human approval", **kwargs: Any) -> dict[str, Any]:
        await self._orch._handle_human_gate(self._state, reason)
        return {"paused": True, "reason": reason}

    async def _finalize_workflow(self, **kwargs: Any) -> dict[str, Any]:
        await self._orch._finalize(self._state)
        return {"finalized": True}

    @staticmethod
    def agent_id_to_tool(agent_id: str) -> str:
        key = normalize_agent_key(agent_id)
        return {
            "scr": "invoke_scr",
            "cma": "invoke_cma",
            "reporting": "invoke_reporting",
            "web": "invoke_web",
            "asm": "invoke_asm",
            "cloudsec": "invoke_cloudsec",
        }.get(key, f"invoke_{key}")
