"""SCR runner — coordinates 10-stage workflow via OpenClaw SDK."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime

from contextlib import asynccontextmanager
from typing import AsyncIterator

from openclaw_sdk import OpenClawClient
from openclaw_sdk.core.config import ClientConfig

from unishield.agents.scr.scr_callback import SCRCallbackHandler
from unishield.agents.scr.scr_prompt_builder import SCRPromptBuilder
from unishield.agents.scr.schemas.input_schema import SCRAgentInput
from unishield.agents.scr.schemas.output_schema import SCRAgentOutput
from unishield.agents.scr.stages.batch_context_guard import BatchContextGuard
from unishield.agents.scr.stages.findings_filter import FilterStats, FindingsFilter
from unishield.agents.scr.tools.repo_acquirer import AcquisitionResult
from unishield.agents.scr.stages.stage1_acquisition import AcquisitionStage
from unishield.agents.scr.stages.stage2_detection import DetectionStage
from unishield.agents.scr.stages.stage3_analysis import AnalysisStage
from unishield.agents.scr.stages.stage7_ai_analysis import AIAnalysisStage
from unishield.agents.scr.stages.stage8_threat_intel import ThreatIntelStage
from unishield.agents.scr.stages.stage9_ranking import RankingStage
from unishield.agents.scr.stages.stage10_output import OutputStage
from unishield.config.settings import Settings, settings
from unishield.infrastructure.kafka_client import KafkaProducer
from unishield.infrastructure.model_router import ModelRouter
from unishield.memory.personal_memory import PersonalMemoryClient
from unishield.agents.scr.tools.tool_requirements import validate_required_tools

logger = logging.getLogger(__name__)


def normalize_agent_key(agent_id: str) -> str:
    return agent_id.lower().replace("unishield-", "")


def _repo_scan_expected(input: SCRAgentInput) -> bool:
    return bool(input.repo_url) and not input.file_paths and not input.raw_code and not input.archive_path


def _empty_repo_scan_message(input: SCRAgentInput) -> str:
    if not input.repo_auth_token:
        return (
            "Repository scan is missing auth token — reconnect the repo with a valid PAT "
            "and retry the scan."
        )
    if not input.repo_ref:
        return (
            "Repository scan is missing branch/ref — set the default branch on the connection "
            "or pass ref_override."
        )
    return (
        "Repository acquisition returned 0 scannable files. Verify the token can read the repo, "
        "the branch/ref exists, and the repository contains supported source files."
    )


class SCRRunner:
    """Runs UniShield-SCR using OpenClaw SDK and local analysis stages."""

    VERSION = "2.0.0"

    def __init__(
        self,
        openclaw_config: ClientConfig,
        shared_memory: SharedMemoryClient,
        personal_memory: PersonalMemoryClient,
        kafka: KafkaProducer,
        app_settings: Settings | None = None,
        model_router: ModelRouter | None = None,
    ) -> None:
        self.openclaw_config = openclaw_config
        self.shared_memory = shared_memory
        self.personal_memory = personal_memory
        self.kafka = kafka
        self.settings = app_settings or settings
        self.model_router = model_router or ModelRouter(self.settings)
        self.prompt_builder = SCRPromptBuilder()
        self._acquisition = AcquisitionStage(personal_memory)
        self._detection = DetectionStage(personal_memory)
        self._analysis = AnalysisStage()
        self._ai = AIAnalysisStage(personal_memory, self.model_router)
        self._threat_intel = ThreatIntelStage(personal_memory, shared_memory)
        self._ranking = RankingStage(personal_memory)
        self._output = OutputStage(personal_memory, shared_memory, kafka, self.VERSION)
        self._findings_filter = FindingsFilter(
            self.model_router,
            use_ai_filtering=self.settings.scr_use_ai_fp_filter,
        )

    @asynccontextmanager
    async def _scr_agent_session(
        self,
        workflow_id: str,
        callback: SCRCallbackHandler,
    ) -> AsyncIterator[object | None]:
        """Yield an OpenClaw SCR agent, or None if the live gateway is unavailable."""
        connect_kwargs = {
            "gateway_ws_url": self.openclaw_config.gateway_ws_url,
            "api_key": self.openclaw_config.api_key,
            "mock_mode": self.openclaw_config.mock_mode,
            "callbacks": [callback],
        }
        if self.openclaw_config.mock_mode:
            async with OpenClawClient.connect(**connect_kwargs) as client:
                yield client.get_agent("unishield-scr", session_name=workflow_id)
            return
        try:
            async with OpenClawClient.connect(**connect_kwargs) as client:
                yield client.get_agent("unishield-scr", session_name=workflow_id)
        except Exception as exc:
            logger.warning(
                "OpenClaw gateway unavailable for workflow %s — continuing with local SCR only: %s",
                workflow_id,
                exc,
            )
            yield None

    async def run(self, input: SCRAgentInput) -> SCRAgentOutput:
        scan_id = input.request_id
        started_at = datetime.now(UTC)
        callback = SCRCallbackHandler(self.personal_memory, scan_id)
        acquisition: AcquisitionResult | None = None
        tools_invoked: list[str] = []
        sbom: dict = {}
        filter_stats = FilterStats()
        file_asts: dict[str, dict] = {}

        try:
            if self.settings.scr_require_tools:
                validate_required_tools()
            async with self._scr_agent_session(input.workflow_id, callback) as agent:
                if agent is not None:
                    await agent.execute(self.prompt_builder.build_acquisition_prompt(input))

                context_guard = BatchContextGuard(self.personal_memory, scan_id)
                await context_guard.write_stage_config(
                    {
                        "output_format": "SCRAgentOutput JSON — no markdown, no truncation",
                        "dedup_required": True,
                        "checkpoint_after_batch": True,
                        "max_fp_score": 0.6,
                    },
                    json.dumps(SCRAgentOutput.model_json_schema()),
                )

                # Stage 1 — acquisition
                acquisition = await self._acquisition.run(scan_id, input)
                files = acquisition.files
                if _repo_scan_expected(input) and len(files) == 0:
                    raise RuntimeError(_empty_repo_scan_message(input))
                if acquisition.archive_path:
                    input = input.model_copy(update={"archive_path": acquisition.archive_path})

                # Stage 2 — language & framework detection
                detection = await self._detection.run(scan_id, files, archive_path=input.archive_path)
                files = self._sort_by_priority(files, input)
                rule_sets = detection.get("rule_sets", {})
                language_map = detection.get("language_map", {})
                languages_detected = detection.get("languages", [])
                frameworks_detected = detection.get("frameworks", [])

                # Stages 3–5 — repo-level SAST, secrets, SBOM (once per scan)
                repo_scan = await self._analysis.process_repo(input, detection)
                tools_invoked.extend(repo_scan.tools_invoked)
                sbom = repo_scan.sbom

                if repo_scan.code_findings:
                    await self.personal_memory.append_findings(
                        scan_id, "repo_sast", repo_scan.code_findings, [], []
                    )
                if repo_scan.secret_findings:
                    await self.personal_memory.append_findings(
                        scan_id, "repo_secrets", [], repo_scan.secret_findings, []
                    )
                if repo_scan.dependency_findings:
                    await self.personal_memory.append_findings(
                        scan_id, "repo_deps", [], [], repo_scan.dependency_findings
                    )

                batches = [
                    files[i : i + self.settings.scr_batch_size]
                    for i in range(0, max(len(files), 1), self.settings.scr_batch_size)
                ]
                if not files:
                    batches = [[]]

                shared_context = await self._load_shared_context(input)
                checkpoint = await self.personal_memory.load_scan_progress(scan_id)

                # Stages 3/4/6 — per-batch dataflow + heuristic supplement
                for batch_num, batch_files in enumerate(batches):
                    batch_id = f"batch-{batch_num}"
                    if checkpoint and batch_id in checkpoint.get("completed_batches", []):
                        continue

                    guard = await context_guard.pre_batch_check(batch_id, batch_num, len(batches))
                    if not guard.should_continue:
                        if guard.stop_reason == "Batch already processed":
                            continue
                        logger.warning("Batch %s aborted: %s", batch_id, guard.stop_reason)
                        break

                    if agent is not None:
                        await agent.execute(
                            self.prompt_builder.build_analysis_prompt(
                                batch_files,
                                batch_id,
                                language_map,
                                shared_context.get("ioc_list", input.ioc_list),
                                input.threat_actor_ttps,
                                input.crown_jewels,
                                guard.output_schema_reminder,
                                guard.refreshed_instructions,
                            )
                        )

                    result = await self._analysis.process_batch(
                        batch_id,
                        batch_files,
                        input,
                        rule_sets,
                        language_map=language_map,
                        repo_code_findings=repo_scan.code_findings,
                        repo_secret_findings=repo_scan.secret_findings,
                    )

                    AnalysisStage.merge_dataflow_enrichments(result.code_findings, result.dataflow_enrichments)
                    for enrichment in result.dataflow_enrichments:
                        ast_payload = enrichment.get("file_ast")
                        if isinstance(ast_payload, dict) and enrichment.get("file_path"):
                            file_asts[str(enrichment["file_path"])] = ast_payload

                    filtered_code, batch_stats = await self._findings_filter.filter_findings(
                        result.code_findings, scan_id, input.client_id
                    )
                    filter_stats.total_input += batch_stats.total_input
                    filter_stats.hard_excluded += batch_stats.hard_excluded
                    filter_stats.ai_excluded += batch_stats.ai_excluded
                    filter_stats.kept += batch_stats.kept
                    filter_stats.ai_filter_failed += batch_stats.ai_filter_failed

                    for finding in filtered_code:
                        fp = self._fingerprint(finding)
                        if await self.personal_memory.fingerprint_exists(scan_id, fp):
                            continue
                        await self.personal_memory.add_fingerprint(scan_id, fp)
                        finding["fingerprint"] = fp

                    await self.personal_memory.append_findings(
                        scan_id,
                        batch_id,
                        filtered_code,
                        result.secret_findings,
                        [],
                    )
                    for fp in batch_files:
                        await self.personal_memory.save_file_scanned(scan_id, fp)

                    progress = await self.personal_memory.load_scan_progress(scan_id) or {}
                    done = list(progress.get("completed_batches", []))
                    if batch_id not in done:
                        done.append(batch_id)
                    await self.personal_memory.save_scan_progress(
                        scan_id, len(batches), done, progress.get("failed_batches", []), batch_id
                    )

                tools_invoked.extend(["dataflow", "heuristic"])

                # Stage 7 — AI semantic analysis
                models_used: list[str] = []
                if input.enable_ai_analysis:
                    models_used = await self._ai.run(scan_id, input)

                # Stage 8 — threat intel correlation
                threat_boost = await self._threat_intel.run(scan_id, input)

                # Stage 9 — ranking
                ranked, secret_findings, dependency_findings, category_counts = await self._ranking.run(scan_id)

                from unishield.attack_path.service import AttackPathService

                attack_service = AttackPathService(self.settings, self.model_router)
                attack_output = await attack_service.analyze(
                    scan_id=scan_id,
                    code_findings=[f.model_dump() for f in ranked],
                    crown_jewels=input.crown_jewels,
                    language_map=language_map,
                    ioc_list=input.ioc_list,
                    file_asts=file_asts,
                )
                attack_summary = AttackPathService.to_shared_memory_summary(attack_output)

                files_scanned = len(await self.personal_memory.get_files_scanned(scan_id))

                # Stage 10 — output assembly
                output = await self._output.run(
                    scan_id,
                    ranked,
                    secret_findings,
                    dependency_findings,
                    input,
                    started_at,
                    files_discovered=len(files),
                    files_scanned=files_scanned,
                    languages_detected=languages_detected,
                    frameworks_detected=frameworks_detected,
                    sbom=sbom,
                    tools_invoked=tools_invoked,
                    models_used=models_used,
                    category_counts=category_counts,
                    threat_intel_boost=threat_boost,
                    attack_summary=attack_summary,
                    filter_stats=filter_stats,
                    ai_filter_enabled=self.settings.scr_use_ai_fp_filter,
                )

                if agent is not None:
                    await agent.execute(
                        self.prompt_builder.build_output_prompt(
                            [f.model_dump() for f in ranked],
                            {"files": len(files), "risk_score": output.risk_score},
                            input.client_id,
                        )
                    )

                return output
        except Exception as exc:
            logger.exception("SCR scan failed for workflow %s", input.workflow_id)
            await self._output.run(
                scan_id,
                [],
                [],
                [],
                input,
                started_at,
                files_discovered=0,
                files_scanned=0,
                languages_detected=[],
                frameworks_detected=[],
                sbom={},
                tools_invoked=tools_invoked,
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
            raise
        finally:
            if acquisition and acquisition.cleanup:
                acquisition.cleanup()

    def _sort_by_priority(self, files: list[str], input: SCRAgentInput) -> list[str]:
        def score(path: str) -> int:
            s = 0
            for jewel in input.crown_jewels:
                if jewel in path:
                    s += 100
            if input.diff_head and path in input.file_paths:
                s += 80
            for kw in ("payment", "auth", "crypto", "swift"):
                if kw in path.lower():
                    s += 60
            for ext in (".env", ".pem", ".key"):
                if path.endswith(ext):
                    s += 40
            for prefix in ("test/", "tests/", "vendor/", "node_modules/"):
                if prefix in path:
                    s -= 50
            return s

        return sorted(files, key=score, reverse=True)

    async def _load_shared_context(self, input: SCRAgentInput) -> dict:
        try:
            return await self.shared_memory.read_agent_output(input.workflow_id, "web")
        except AgentOutputNotReady:
            return {}

    def _fingerprint(self, finding: dict) -> str:
        key = f"{finding.get('file_path')}:{finding.get('line_start')}:{finding.get('category')}"
        return hashlib.sha256(key.encode()).hexdigest()
