"""SCR Python tool host — scanners run only when invoked by the skill executor."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from backend.scr.agent_tools import SCRAgentTools, TOOL_CATALOG
from backend.scr.schemas.input_schema import SCRAgentInput
from backend.scr.schemas.output_schema import SCRAgentOutput
from backend.scr.schemas.output_schema import CodeFinding
from backend.scr.stages.batch_context_guard import BatchContextGuard
from backend.scr.stages.findings_filter import FilterStats
from backend.scr.stages.stage3_analysis import AnalysisStage
from backend.scr.tools.repo_acquirer import AcquisitionResult
from backend.scr.tools.scanner_integration import sbom_summary
from backend.scr.tools.tool_requirements import validate_required_tools
from backend.scr.scr_runner import _empty_repo_scan_message, _repo_scan_expected

if TYPE_CHECKING:
    from backend.scr.scr_runner import SCRRunner

logger = logging.getLogger(__name__)

CANONICAL_TOOL_SEQUENCE = [
    "run_acquisition",
    "run_detection",
    "run_repo_scans",
    "run_batch_analysis",
    "run_ai_enrichment",
    "run_threat_intel",
    "run_ranking",
    "run_attack_path",
    "assemble_output",
]


@dataclass
class SCRScanContext:
    """Mutable scan state shared across tool invocations."""

    input: SCRAgentInput
    scan_id: str
    started_at: datetime
    acquisition: AcquisitionResult | None = None
    files: list[str] = field(default_factory=list)
    detection: dict = field(default_factory=dict)
    repo_scan: Any = None
    sbom: dict = field(default_factory=dict)
    tools_invoked: list[str] = field(default_factory=list)
    filter_stats: FilterStats = field(default_factory=FilterStats)
    file_asts: dict[str, dict] = field(default_factory=dict)
    models_used: list[str] = field(default_factory=list)
    threat_boost: int = 0
    ranked: list[CodeFinding] = field(default_factory=list)
    secret_findings: list = field(default_factory=list)
    dependency_findings: list = field(default_factory=list)
    category_counts: dict = field(default_factory=dict)
    attack_summary: dict = field(default_factory=dict)
    output: SCRAgentOutput | None = None
    repo_context: dict | None = None


class SCRToolHost:
    """Registers SCR stage handlers as agent-invokable tools."""

    def __init__(self, runner: "SCRRunner", scan_input: SCRAgentInput) -> None:
        self._runner = runner
        self._ctx = SCRScanContext(
            input=scan_input,
            scan_id=scan_input.request_id,
            started_at=datetime.now(UTC),
        )
        self._tools = SCRAgentTools()
        self._register_tools()

    @property
    def context(self) -> SCRScanContext:
        return self._ctx

    @property
    def tools(self) -> SCRAgentTools:
        return self._tools

    def _register_tools(self) -> None:
        for name in CANONICAL_TOOL_SEQUENCE:
            self._tools.register(name, getattr(self, f"_{name}"))

    async def run_canonical_sequence(self) -> SCRAgentOutput:
        """Execute the full SCR pipeline via tools in skill-spec order."""
        for name in CANONICAL_TOOL_SEQUENCE:
            logger.info("SCR skill tool: %s", name)
            await self._tools.invoke(name)
        if not self._ctx.output:
            raise RuntimeError("SCR pipeline completed without assemble_output")
        return self._ctx.output

    async def _run_acquisition(self) -> dict[str, Any]:
        runner = self._runner
        ctx = self._ctx
        progress = runner.progress
        if progress:
            await progress.set_stage(ctx.input.workflow_id, "acquisition", "running")
        if runner.settings.scr_require_tools and not ctx.input.skip_tool_check:
            validate_required_tools()
        elif ctx.input.skip_tool_check:
            validate_required_tools(strict=False)

        ctx.acquisition = await runner._acquisition.run(ctx.scan_id, ctx.input)
        ctx.files = ctx.acquisition.files
        if progress:
            await progress.set_stage(
                ctx.input.workflow_id, "acquisition", "done", detail=f"{len(ctx.files)} files"
            )
        if _repo_scan_expected(ctx.input) and len(ctx.files) == 0:
            raise RuntimeError(_empty_repo_scan_message(ctx.input))
        if ctx.acquisition.archive_path:
            ctx.input = ctx.input.model_copy(update={"archive_path": ctx.acquisition.archive_path})
            self._ctx.input = ctx.input
        return {"files": len(ctx.files)}

    async def _run_detection(self) -> dict[str, Any]:
        runner = self._runner
        ctx = self._ctx
        if runner.progress:
            await runner.progress.set_stage(ctx.input.workflow_id, "detection", "running")
        ctx.detection = await runner._detection.run(
            ctx.scan_id, ctx.files, archive_path=ctx.input.archive_path
        )
        ctx.files = runner._sort_by_priority(ctx.files, ctx.input)
        if runner.progress:
            await runner.progress.set_stage(
                ctx.input.workflow_id,
                "detection",
                "done",
                detail=f"{len(ctx.detection.get('languages', []))} languages",
            )
        return {"languages": ctx.detection.get("languages", [])}

    async def _run_repo_scans(self) -> dict[str, Any]:
        runner = self._runner
        ctx = self._ctx
        if runner.progress:
            await runner.progress.set_stage(ctx.input.workflow_id, "sast", "running")
        ctx.repo_scan = await runner._analysis.process_repo(ctx.input, ctx.detection)
        ctx.sbom = ctx.repo_scan.sbom
        ctx.tools_invoked.extend(ctx.repo_scan.tools_invoked)
        if runner.progress:
            await runner.progress.set_stage(
                ctx.input.workflow_id,
                "sast",
                "done",
                detail=f"{len(ctx.repo_scan.code_findings)} findings",
            )
            await runner.progress.set_stage(
                ctx.input.workflow_id,
                "secrets",
                "done",
                detail=f"{len(ctx.repo_scan.secret_findings)} secrets",
            )
            await runner.progress.set_stage(
                ctx.input.workflow_id,
                "sbom",
                "done",
                detail=f"{len(ctx.repo_scan.dependency_findings)} deps",
            )
        if ctx.repo_scan.code_findings:
            await runner.personal_memory.append_findings(
                ctx.scan_id, "repo_sast", ctx.repo_scan.code_findings, [], []
            )
        if ctx.repo_scan.secret_findings:
            await runner.personal_memory.append_findings(
                ctx.scan_id, "repo_secrets", [], ctx.repo_scan.secret_findings, []
            )
        if ctx.repo_scan.dependency_findings:
            await runner.personal_memory.append_findings(
                ctx.scan_id, "repo_deps", [], [], ctx.repo_scan.dependency_findings
            )
        return {
            "code_findings": len(ctx.repo_scan.code_findings),
            "secret_findings": len(ctx.repo_scan.secret_findings),
        }

    async def _run_batch_analysis(self) -> dict[str, Any]:
        runner = self._runner
        ctx = self._ctx
        detection = ctx.detection
        rule_sets = detection.get("rule_sets", {})
        language_map = detection.get("language_map", {})
        batch_size = runner.settings.scr_batch_size
        files = ctx.files
        batches = [files[i : i + batch_size] for i in range(0, max(len(files), 1), batch_size)]
        if not files:
            batches = [[]]

        context_guard = BatchContextGuard(runner.personal_memory, ctx.scan_id)
        shared_context = await runner._load_shared_context(ctx.input)
        checkpoint = await runner.personal_memory.load_scan_progress(ctx.scan_id)

        if runner.progress:
            await runner.progress.set_stage(ctx.input.workflow_id, "dataflow", "running")

        for batch_num, batch_files in enumerate(batches):
            batch_id = f"batch-{batch_num}"
            if checkpoint and batch_id in checkpoint.get("completed_batches", []):
                continue
            guard = await context_guard.pre_batch_check(batch_id, batch_num, len(batches))
            if not guard.should_continue:
                if guard.stop_reason == "Batch already processed":
                    continue
                break

            result = await runner._analysis.process_batch(
                batch_id,
                batch_files,
                ctx.input,
                rule_sets,
                language_map=language_map,
                repo_code_findings=ctx.repo_scan.code_findings,
                repo_secret_findings=ctx.repo_scan.secret_findings,
            )
            AnalysisStage.merge_dataflow_enrichments(result.code_findings, result.dataflow_enrichments)
            for enrichment in result.dataflow_enrichments:
                ast_payload = enrichment.get("file_ast")
                if isinstance(ast_payload, dict) and enrichment.get("file_path"):
                    ctx.file_asts[str(enrichment["file_path"])] = ast_payload

            filtered_code, batch_stats = await runner._findings_filter.filter_findings(
                result.code_findings, ctx.scan_id, ctx.input.client_id
            )
            ctx.filter_stats.total_input += batch_stats.total_input
            ctx.filter_stats.hard_excluded += batch_stats.hard_excluded
            ctx.filter_stats.ai_excluded += batch_stats.ai_excluded
            ctx.filter_stats.kept += batch_stats.kept
            ctx.filter_stats.ai_filter_failed += batch_stats.ai_filter_failed

            for finding in filtered_code:
                fp = runner._fingerprint(finding)
                if await runner.personal_memory.fingerprint_exists(ctx.scan_id, fp):
                    continue
                await runner.personal_memory.add_fingerprint(ctx.scan_id, fp)
                finding["fingerprint"] = fp

            await runner.personal_memory.append_findings(
                ctx.scan_id, batch_id, filtered_code, result.secret_findings, []
            )
            for fp in batch_files:
                await runner.personal_memory.save_file_scanned(ctx.scan_id, fp)

            batch_progress = await runner.personal_memory.load_scan_progress(ctx.scan_id) or {}
            done = list(batch_progress.get("completed_batches", []))
            if batch_id not in done:
                done.append(batch_id)
            await runner.personal_memory.save_scan_progress(
                ctx.scan_id, len(batches), done, batch_progress.get("failed_batches", []), batch_id
            )

        ctx.tools_invoked.extend(["dataflow", "heuristic"])
        if runner.progress:
            await runner.progress.set_stage(
                ctx.input.workflow_id, "dataflow", "done", detail=f"{len(batches)} batches"
            )
        return {"batches": len(batches)}

    async def _run_ai_enrichment(self) -> dict[str, Any]:
        runner = self._runner
        ctx = self._ctx
        if not ctx.input.enable_ai_analysis:
            return {"skipped": True}
        if runner.progress:
            await runner.progress.set_stage(ctx.input.workflow_id, "ai_analysis", "running")
        ctx.models_used = await runner._ai.run(ctx.scan_id, ctx.input)
        if runner.progress:
            await runner.progress.set_stage(ctx.input.workflow_id, "ai_analysis", "done")
        return {"models": ctx.models_used}

    async def _run_threat_intel(self) -> dict[str, Any]:
        runner = self._runner
        ctx = self._ctx
        if runner.progress:
            await runner.progress.set_stage(ctx.input.workflow_id, "threat_intel", "running")
        ctx.threat_boost = await runner._threat_intel.run(ctx.scan_id, ctx.input)
        if runner.progress:
            await runner.progress.set_stage(ctx.input.workflow_id, "threat_intel", "done")
        return {"boost": ctx.threat_boost}

    async def _run_ranking(self) -> dict[str, Any]:
        runner = self._runner
        ctx = self._ctx
        if runner.progress:
            await runner.progress.set_stage(ctx.input.workflow_id, "ranking", "running")
        ranked, secrets, deps, categories = await runner._ranking.run(ctx.scan_id)
        ctx.ranked = ranked
        ctx.secret_findings = secrets
        ctx.dependency_findings = deps
        ctx.category_counts = categories
        if runner.progress:
            await runner.progress.set_stage(
                ctx.input.workflow_id, "ranking", "done", detail=f"{len(ranked)} ranked"
            )
        return {"ranked": len(ranked)}

    async def _run_attack_path(self) -> dict[str, Any]:
        from backend.attack_path.service import AttackPathService

        runner = self._runner
        ctx = self._ctx
        attack_service = AttackPathService(runner.settings, runner.model_router)
        attack_output = await attack_service.analyze(
            scan_id=ctx.scan_id,
            code_findings=[f.model_dump() for f in ctx.ranked],
            crown_jewels=ctx.input.crown_jewels,
            language_map=ctx.detection.get("language_map", {}),
            ioc_list=ctx.input.ioc_list,
            file_asts=ctx.file_asts,
        )
        ctx.attack_summary = AttackPathService.to_shared_memory_summary(attack_output)
        return ctx.attack_summary

    async def _assemble_output(self) -> dict[str, Any]:
        runner = self._runner
        ctx = self._ctx
        files_scanned = len(await runner.personal_memory.get_files_scanned(ctx.scan_id))
        if runner.progress:
            await runner.progress.set_stage(ctx.input.workflow_id, "output", "running")

        ctx.output = await runner._output.run(
            ctx.scan_id,
            ctx.ranked,
            ctx.secret_findings,
            ctx.dependency_findings,
            ctx.input,
            ctx.started_at,
            files_discovered=len(ctx.files),
            files_scanned=files_scanned,
            languages_detected=ctx.detection.get("languages", []),
            frameworks_detected=ctx.detection.get("frameworks", []),
            sbom=ctx.sbom,
            tools_invoked=ctx.tools_invoked,
            models_used=ctx.models_used,
            category_counts=ctx.category_counts,
            threat_intel_boost=ctx.threat_boost,
            attack_summary=ctx.attack_summary,
            filter_stats=ctx.filter_stats,
            ai_filter_enabled=runner.settings.scr_use_ai_fp_filter,
        )

        if runner.action_gate and ctx.output.scan_status == "COMPLETED":
            from backend.scr.hitl_proposals import propose_finding_reviews

            try:
                await propose_finding_reviews(
                    runner.action_gate,
                    workflow_id=ctx.input.workflow_id,
                    findings=[f.model_dump() for f in ctx.ranked],
                    risk_score=ctx.output.risk_score,
                )
            except Exception as exc:
                logger.warning("HITL proposal registration failed: %s", exc)

        if runner.repo_memory and ctx.input.connection_id:
            await runner.repo_memory.save_scan_summary(
                ctx.input.client_id,
                ctx.input.connection_id,
                workflow_id=ctx.input.workflow_id,
                risk_score=ctx.output.risk_score,
                finding_count=ctx.output.total_findings,
                languages=ctx.detection.get("languages", []),
                frameworks=ctx.detection.get("frameworks", []),
            )

        if runner.progress:
            await runner.progress.set_stage(ctx.input.workflow_id, "output", "done")
            await runner.progress.complete(ctx.input.workflow_id)

        return {
            "scan_status": ctx.output.scan_status,
            "risk_score": ctx.output.risk_score,
            "total_findings": ctx.output.total_findings,
        }
