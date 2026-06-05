"""Register OpenClaw mock handlers aligned with UniShield skill contracts."""

from __future__ import annotations

import json
import logging

from openclaw_sdk.client import MOCK_RESPONSE_HANDLERS

from backend.agents.skill_loader import load_skill

logger = logging.getLogger(__name__)


async def _scr_mock_handler(query: str) -> str:
    """Acknowledge SCR stage prompts during local/mock execution."""
    try:
        payload = json.loads(query)
        stage = payload.get("stage", "unknown")
    except (json.JSONDecodeError, TypeError):
        stage = "unknown"
    return json.dumps(
        {
            "agent": "unishield-scr",
            "status": "acknowledged",
            "stage": stage,
            "mode": "local_runner",
            "message": "SCR local pipeline owns analysis; OpenClaw session tracks lifecycle.",
        }
    )


async def _orchestrator_mock_handler(query: str) -> str:
    return json.dumps(
        {
            "agent": "unishield-orchestrator",
            "status": "acknowledged",
            "mode": "local_runner",
            "message": "Orchestrator routing handled by Python WorkflowEngine.",
        }
    )


def configure_openclaw_agents() -> None:
    """Load skills and register mock handlers for dev/test OpenClaw sessions."""
    skills = {
        "unishield-scr": load_skill("unishield-scr"),
        "unishield-orchestrator": load_skill("unishield-orchestrator"),
    }
    for agent_id, content in skills.items():
        if content:
            logger.info("Loaded skill for %s (%d chars)", agent_id, len(content))

    MOCK_RESPONSE_HANDLERS["unishield-scr"] = _scr_mock_handler
    MOCK_RESPONSE_HANDLERS["unishield-orchestrator"] = _orchestrator_mock_handler
