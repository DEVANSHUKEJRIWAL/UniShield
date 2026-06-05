"""Register OpenClaw agents — mock handlers only when mock mode is enabled."""

from __future__ import annotations

import json
import logging

from openclaw_sdk.client import MOCK_RESPONSE_HANDLERS

from backend.agents.skill_loader import load_all_skills

logger = logging.getLogger(__name__)


async def _scr_mock_handler(query: str) -> str:
    raise RuntimeError(
        "OpenClaw mock mode is disabled. Start the live OpenClaw gateway "
        "or set OPENCLAW_MOCK_MODE=true only for automated tests."
    )


async def _orchestrator_mock_handler(query: str) -> str:
    raise RuntimeError(
        "OpenClaw mock mode is disabled. Start the live OpenClaw gateway "
        "or set OPENCLAW_MOCK_MODE=true only for automated tests."
    )


def configure_openclaw_agents(*, mock_mode: bool = False) -> dict[str, str]:
    """Load skills; register mock handlers only in explicit mock/test mode."""
    skills = load_all_skills()
    for agent_id, content in skills.items():
        if content:
            logger.info("Loaded skill for %s (%d chars)", agent_id, len(content))
        else:
            logger.warning("Missing skill file for %s", agent_id)

    if mock_mode:
        async def _test_scr_handler(query: str) -> str:
            try:
                payload = json.loads(query)
            except json.JSONDecodeError:
                payload = {}
            return json.dumps(
                {
                    "agent": "unishield-scr",
                    "status": "acknowledged",
                    "stage": payload.get("stage", "unknown"),
                    "mode": "test_mock",
                }
            )

        async def _test_orchestrator_handler(query: str) -> str:
            return json.dumps({"agent": "unishield-orchestrator", "status": "acknowledged", "mode": "test_mock"})

        MOCK_RESPONSE_HANDLERS["unishield-scr"] = _test_scr_handler
        MOCK_RESPONSE_HANDLERS["unishield-orchestrator"] = _test_orchestrator_handler
    else:
        MOCK_RESPONSE_HANDLERS.pop("unishield-scr", None)
        MOCK_RESPONSE_HANDLERS.pop("unishield-orchestrator", None)

    return skills
