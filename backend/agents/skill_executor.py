"""Execute OpenClaw agents with SKILL.md injected as system context."""

from __future__ import annotations

import json
import logging
from typing import Any

from openclaw_sdk.core.types import ExecutionResult

from backend.agents.skill_loader import load_skill

logger = logging.getLogger(__name__)

_SCR_TOOL_CATALOG: list[dict] | None = None


def _scr_tools() -> list[dict]:
    global _SCR_TOOL_CATALOG
    if _SCR_TOOL_CATALOG is None:
        try:
            from backend.scr.agent_tools import TOOL_CATALOG

            _SCR_TOOL_CATALOG = TOOL_CATALOG
        except ImportError:
            _SCR_TOOL_CATALOG = []
    return _SCR_TOOL_CATALOG


def build_skill_message(
    agent_id: str,
    payload: dict[str, Any],
    *,
    stage: str | None = None,
    output_schema: dict | None = None,
    repo_context: dict | None = None,
) -> str:
    """Build a user message that embeds the agent skill contract and task payload."""
    skill_text = load_skill(agent_id)
    body: dict[str, Any] = {
        "agent_id": agent_id,
        "stage": stage,
        "skill_contract": skill_text,
        "task_payload": payload,
        "response_rules": [
            "Follow the skill contract exactly.",
            "Respond with a single valid JSON object when output schema is provided.",
            "Do not wrap JSON in markdown fences.",
            "Never truncate required arrays.",
        ],
    }
    if output_schema is not None:
        body["output_schema"] = output_schema
    if repo_context:
        body["repo_memory"] = repo_context
    if agent_id == "unishield-scr":
        body["available_tools"] = _scr_tools()
        body["execution_mode"] = "skill_first"
    return json.dumps(body, default=str)


async def execute_with_skill(
    agent,
    agent_id: str,
    payload: dict[str, Any],
    *,
    stage: str | None = None,
    output_schema: dict | None = None,
    repo_context: dict | None = None,
) -> ExecutionResult:
    """Invoke an OpenClaw agent handle with its SKILL.md as system prompt."""
    skill_text = load_skill(agent_id)
    message = build_skill_message(
        agent_id,
        payload,
        stage=stage,
        output_schema=output_schema,
        repo_context=repo_context,
    )
    logger.info(
        "OpenClaw skill execution agent=%s stage=%s skill_chars=%d",
        agent_id,
        stage or "full",
        len(skill_text),
    )
    return await agent.execute(message, system_prompt=skill_text or None)


def parse_json_response(content: str) -> dict[str, Any] | None:
    """Best-effort parse of agent JSON output."""
    text = (content or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None
    return None
