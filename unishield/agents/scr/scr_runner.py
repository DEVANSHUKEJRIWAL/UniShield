"""SCR runner — coordinates 10-stage workflow via OpenClaw SDK."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
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
from unishield.agents.scr.stages.findings_filter import FindingsFilter
from unishield.agents.scr.tools.repo_acquirer import AcquisitionResult
from unishield.agents.scr.stages.stage1_acquisition import AcquisitionStage
from unishield.agents.scr.stages.stage2_detection import DetectionStage
from unishield.agents.scr.stages.stage3_analysis import AnalysisStage
from unishield.agents.scr.stages.stage7_ai_analysis import AIAnalysisStage
from unishield.agents.scr.stages.stage8_threat_intel import ThreatIntelStage
from unishield.agents.scr.stages.stage9_ranking import RankingStage
from unishield.config.settings import Settings, settings
from unishield.infrastructure.kafka_client import KafkaProducer
from unishield.infrastructure.model_router import ModelRouter
from unishield.memory.personal_memory import PersonalMemoryClient
from unishield.memory.shared_memory import AgentOutputNotReady, SharedMemoryClient

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

    VERSION = "1.0.0"

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
        self._ai = AIAnalysisStage(personal_memory)
        self._threat_intel = ThreatIntelStage(personal_memory, shared_memory)
        self._ranking = RankingStage(personal_memory)
        self._findings_filter = FindingsFilter(self.model_router)

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

        try:
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

                acquisition = await self._acquisition.run(scan_id, input)
                files = acquisition.files
                if _repo_scan_expected(input) and len(files) == 0:
                    raise RuntimeError(_empty_repo_scan_message(input))
                if acquisition.archive_path:
                    input = input.model_copy(update={"archive_path": acquisition.archive_path})

                detection = await self._detection.run(scan_id, files)
                files = self._sort_by_priority(files, input)
                rule_sets = detection.get("rule_sets", {})
                language_map = detection.get("language_map", {})

                batches = [
                    files[i : i + self.settings.scr_batch_size]
                    for i in range(0, max(len(files), 1), self.settings.scr_batch_size)
                ]
                if not files:
                    batches = [[]]

                shared_context = await self._load_shared_context(input)
                checkpoint = await self.personal_memory.load_scan_progress(scan_id)
                file_asts: dict[str, dict] = {}

                for batch_num, batch_files in enumerate(batches):
                    batch_id = f"batch-{batch_num}"
                    guard = await context_guard.pre_batch_check(batch_id, batch_num, len(batches))
                    if not guard.should_continue:
                        logger.warning("Batch %s aborted: %s", batch_id, guard.stop_reason)
                        break

                    if checkpoint and batch_id in checkpoint.get("completed_batches", []):
                        continue

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
                        batch_id, batch_files, input, rule_sets, language_map=language_map
                    )

                    for enrichment in result.dataflow_enrichments:
                        ast_payload = enrichment.get("file_ast")
                        if isinstance(ast_payload, dict) and enrichment.get("file_path"):
                            file_asts[str(enrichment["file_path"])] = ast_payload

                    filtered_code, _stats = await self._findings_filter.filter_findings(
                        result.code_findings, scan_id, input.client_id
                    )

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
                        result.dependency_findings,
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

                if input.enable_ai_analysis:
                    await self._ai.run(scan_id, input)

                await self._threat_intel.run(scan_id, input)
                ranked = await self._ranking.run(scan_id)
                all_findings = await self.personal_memory.load_all_findings(scan_id)
                completed_at = datetime.now(UTC)

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

                severity_counts: dict[str, int] = {}
                for f in ranked:
                    sev = f.severity.upper()
                    severity_counts[sev] = severity_counts.get(sev, 0) + 1

                risk_score = min(
                    100,
                    severity_counts.get("CRITICAL", 0) * 30
                    + severity_counts.get("HIGH", 0) * 15
                    + len(all_findings["secrets"]) * 20,
                )
                risk_label = (
                    "CRITICAL" if risk_score >= 80 else "HIGH" if risk_score >= 50 else "MEDIUM" if risk_score >= 25 else "LOW"
                )

                output = SCRAgentOutput(
                    scan_id=scan_id,
                    request_id=input.request_id,
                    client_id=input.client_id,
                    scan_mode=str(input.scan_mode),
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_seconds=(completed_at - started_at).total_seconds(),
                    scan_status="COMPLETED",
                    files_discovered=len(files),
                    files_scanned=len(await self.personal_memory.get_files_scanned(scan_id)),
                    files_skipped=0,
                    lines_analyzed=len(files) * 100,
                    risk_score=risk_score,
                    risk_label=risk_label,
                    total_findings=len(ranked) + len(all_findings["secrets"]),
                    findings_by_severity=severity_counts,
                    code_findings=ranked,
                    agent_version=self.VERSION,
                    tools_invoked=["sast", "secrets", "sbom", "dataflow", "findings_filter"],
                )

                if agent is not None:
                    await agent.execute(
                        self.prompt_builder.build_output_prompt(
                            [f.model_dump() for f in ranked],
                            {"files": len(files), "risk_score": risk_score},
                            input.client_id,
                        )
                    )

                await self._write_shared_output(
                    input,
                    risk_score=risk_score,
                    risk_label=risk_label,
                    severity_counts=severity_counts,
                    ranked=ranked,
                    all_findings=all_findings,
                    attack_summary=attack_summary,
                    output=output,
                    completed_at=completed_at,
                    files_discovered=len(files),
                )

                await self.personal_memory.expire_all(scan_id)
                await self.kafka.publish(
                    "agent.complete",
                    {
                        "agent_id": "unishield-scr",
                        "workflow_id": input.workflow_id,
                        "scan_id": scan_id,
                        "risk_score": risk_score,
                        "client_id": input.client_id,
                        "status": "SUCCESS",
                    },
                    key=input.workflow_id,
                )
                return output
        except Exception as exc:
            logger.exception("SCR scan failed for workflow %s", input.workflow_id)
            await self._write_shared_output(
                input,
                risk_score=0,
                risk_label="LOW",
                severity_counts={},
                ranked=[],
                all_findings={"secrets": [], "code": [], "dependencies": []},
                attack_summary={
                    "total_paths": 0,
                    "crown_jewel_paths": 0,
                    "top_chokepoint": None,
                    "highest_blast_score": 0,
                },
                output=None,
                completed_at=datetime.now(UTC),
                files_discovered=0,
                scan_status="FAILED",
                error_message=str(exc),
            )
            raise
        finally:
            if acquisition and acquisition.cleanup:
                acquisition.cleanup()

    async def _write_shared_output(
        self,
        input: SCRAgentInput,
        *,
        risk_score: int,
        risk_label: str,
        severity_counts: dict[str, int],
        ranked: list,
        all_findings: dict,
        attack_summary: dict,
        output: SCRAgentOutput | None,
        completed_at: datetime,
        files_discovered: int,
        scan_status: str = "COMPLETED",
        error_message: str | None = None,
    ) -> None:
        payload: dict = {
            "agent_id": "scr",
            "completed_at": completed_at.isoformat(),
            "risk_score": risk_score,
            "highest_severity": risk_label,
            "requires_human_approval": risk_score >= 80,
            "auto_remediation_safe": risk_score < 50,
            "forward_to": [],
            "critical_count": severity_counts.get("CRITICAL", 0),
            "secret_findings_count": len(all_findings.get("secrets", [])),
            "correlated_to_incident": bool(input.active_incident_id),
            "top_findings": [f.model_dump() for f in ranked[:10]],
            "sbom_summary": output.sbom_summary if output else {},
            "compliance_gaps": output.compliance_gaps if output else [],
            "attack_paths_summary": attack_summary,
            "scan_status": scan_status,
            "files_discovered": files_discovered,
        }
        if error_message:
            payload["error_message"] = error_message
        await self.shared_memory.write_agent_output(input.workflow_id, "scr", payload)

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
