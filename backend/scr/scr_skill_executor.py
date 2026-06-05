"""Execute SCR via OpenClaw skill session + Python tool host."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.agents.skill_executor import execute_with_skill, parse_json_response
from backend.scr.schemas.input_schema import SCRAgentInput
from backend.scr.schemas.output_schema import SCRAgentOutput
from backend.scr.scr_tool_host import CANONICAL_TOOL_SEQUENCE, SCRToolHost
from backend.scr.skill_pipeline import SkillFirstPipeline

if TYPE_CHECKING:
    from backend.scr.scr_runner import SCRRunner

logger = logging.getLogger(__name__)


class SCRSkillExecutor:
    """Skill-first SCR: OpenClaw agent orchestrates; Python tools execute."""

    def __init__(self, runner: "SCRRunner") -> None:
        self._runner = runner

    async def run(self, scan_input: SCRAgentInput) -> SCRAgentOutput:
        runner = self._runner
        progress = runner.progress
        if progress:
            await progress.start(scan_input.workflow_id)

        repo_context = None
        if runner.repo_memory and scan_input.connection_id:
            repo_context = await runner.repo_memory.load(scan_input.client_id, scan_input.connection_id)

        host = SCRToolHost(runner, scan_input)
        host.context.repo_context = repo_context
        callback = __import__(
            "backend.scr.scr_callback", fromlist=["SCRCallbackHandler"]
        ).SCRCallbackHandler(runner.personal_memory, scan_input.request_id)

        try:
            async with runner._scr_agent_session(scan_input.workflow_id, callback) as agent:
                if agent is None:
                    raise RuntimeError(
                        "OpenClaw SCR agent required for skill-first mode — "
                        "start the gateway or set SCR_EXECUTION_MODE=local"
                    )

                await execute_with_skill(
                    agent,
                    "unishield-scr",
                    {
                        **scan_input.model_dump(mode="json"),
                        "mode": "skill_first_start",
                        "available_tools": host.tools.catalog(),
                        "canonical_sequence": CANONICAL_TOOL_SEQUENCE,
                    },
                    stage="skill_start",
                    output_schema=SCRAgentOutput.model_json_schema(),
                    repo_context=repo_context,
                )

                output = await self._execute_tools(agent, host, scan_input, repo_context)

                await execute_with_skill(
                    agent,
                    "unishield-scr",
                    {
                        "mode": "skill_first_complete",
                        "scan_status": output.scan_status,
                        "risk_score": output.risk_score,
                        "total_findings": output.total_findings,
                        "output": output.model_dump(mode="json"),
                    },
                    stage="skill_complete",
                    repo_context=repo_context,
                )
                return output
        except Exception as exc:
            logger.exception("Skill-first SCR failed for workflow %s", scan_input.workflow_id)
            if progress:
                await progress.fail(scan_input.workflow_id, str(exc))
            try:
                await runner._output.run(
                    scan_input.request_id,
                    [],
                    [],
                    [],
                    scan_input,
                    host.context.started_at,
                    files_discovered=0,
                    files_scanned=0,
                    languages_detected=[],
                    frameworks_detected=[],
                    sbom={},
                    tools_invoked=host.context.tools_invoked,
                    models_used=[],
                    category_counts={},
                    threat_intel_boost=0,
                    attack_summary={
                        "total_paths": 0,
                        "crown_jewel_paths": 0,
                        "top_chokepoint": None,
                        "highest_blast_score": 0,
                    },
                    scan_status="FAILED",
                    error_message=str(exc),
                )
            except Exception:
                logger.exception("Failed to write SCR failure output")
            raise
        finally:
            if host.context.acquisition and host.context.acquisition.cleanup:
                host.context.acquisition.cleanup()

    async def _execute_tools(
        self,
        agent,
        host: SCRToolHost,
        scan_input: SCRAgentInput,
        repo_context: dict | None,
    ) -> SCRAgentOutput:
        settings = self._runner.settings
        if self._runner.openclaw_config.mock_mode or settings.scr_skill_scripted:
            return await host.run_canonical_sequence()

        pipeline = SkillFirstPipeline(host.tools)
        context = await pipeline.run(agent, scan_input, repo_context=repo_context)
        if host.context.output:
            return host.context.output

        completed = set(context.get("stages_completed") or [])
        missing = [t for t in CANONICAL_TOOL_SEQUENCE if t not in completed]
        if missing:
            logger.warning("LLM skill loop incomplete — running remaining tools: %s", missing)
            for tool_name in missing:
                await host.tools.invoke(tool_name)

        if not host.context.output:
            raise RuntimeError("SCR skill pipeline did not produce output")
        return host.context.output
