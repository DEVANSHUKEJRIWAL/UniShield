"""Skill-first SCR pipeline — OpenClaw drives stages, Python tools execute scans."""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.agents.skill_executor import execute_with_skill, parse_json_response
from backend.scr.agent_tools import SCRAgentTools, TOOL_CATALOG
from backend.scr.schemas.input_schema import SCRAgentInput

logger = logging.getLogger(__name__)

MAX_SKILL_ITERATIONS = 24


class SkillFirstPipeline:
    """LLM/OpenClaw orchestrates SCR stages; Python tools perform analysis."""

    def __init__(self, tools: SCRAgentTools) -> None:
        self._tools = tools

    async def run(
        self,
        agent,
        input: SCRAgentInput,
        *,
        repo_context: dict | None = None,
    ) -> dict[str, Any]:
        """Run skill-first loop until agent signals pipeline_complete or max iterations."""
        context: dict[str, Any] = {
            "scan_id": input.request_id,
            "workflow_id": input.workflow_id,
            "client_id": input.client_id,
            "input": input.model_dump(mode="json"),
            "tool_results": {},
            "stages_completed": [],
        }
        tool_manifest = self._tools.catalog()

        for iteration in range(MAX_SKILL_ITERATIONS):
            payload = {
                "mode": "skill_first",
                "iteration": iteration,
                "available_tools": tool_manifest,
                "pipeline_context": context,
                "instructions": [
                    "You orchestrate the SCR 10-stage pipeline.",
                    "Call tools by responding with {\"tool_call\": {\"name\": \"...\", \"args\": {...}}}.",
                    "When all stages are done respond with {\"pipeline_complete\": true}.",
                    "Never run scanners yourself — always invoke the matching tool.",
                ],
            }
            result = await execute_with_skill(
                agent,
                "unishield-scr",
                payload,
                stage=f"skill_iter_{iteration}",
                repo_context=repo_context,
            )
            parsed = parse_json_response(result.content or "")
            if not parsed:
                logger.warning("Skill iteration %d returned no JSON — stopping", iteration)
                break

            if parsed.get("pipeline_complete"):
                logger.info("Skill-first SCR pipeline complete at iteration %d", iteration)
                return context

            tool_call = parsed.get("tool_call")
            if not isinstance(tool_call, dict):
                continue
            name = tool_call.get("name")
            args = tool_call.get("args") or {}
            if not name:
                continue
            try:
                tool_result = await self._tools.invoke(str(name), **args)
                context["tool_results"][str(name)] = tool_result
                context["stages_completed"].append(str(name))
            except Exception as exc:
                logger.exception("Tool %s failed in skill pipeline", name)
                context.setdefault("tool_errors", []).append({"tool": name, "error": str(exc)})
                if parsed.get("abort_on_error"):
                    raise

        return context
