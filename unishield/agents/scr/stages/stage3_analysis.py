"""Stage 3 — repo-level and per-batch analysis worker pool."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field

from unishield.agents.scr.schemas.input_schema import SCRAgentInput
from unishield.agents.scr.tools.dataflow_analyzer import DataflowAnalyzer
from unishield.agents.scr.tools.sast_runner import SASTRunner
from unishield.agents.scr.tools.sbom_generator import SBOMGenerator
from unishield.agents.scr.tools.secrets_scanner import SecretsScanner
from unishield.agents.scr.tools.repo_acquirer import read_repo_file

logger = logging.getLogger(__name__)


@dataclass
class RepoScanResult:
    code_findings: list[dict] = field(default_factory=list)
    secret_findings: list[dict] = field(default_factory=list)
    dependency_findings: list[dict] = field(default_factory=list)
    sbom: dict = field(default_factory=dict)
    tools_invoked: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class BatchResult:
    batch_id: str
    code_findings: list[dict] = field(default_factory=list)
    secret_findings: list[dict] = field(default_factory=list)
    dependency_findings: list[dict] = field(default_factory=list)
    sbom_components: list[dict] = field(default_factory=list)
    dataflow_enrichments: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class AnalysisStage:
    """Parallel worker pool for SAST, secrets, SBOM, and dataflow analysis."""

    def __init__(self) -> None:
        self.sast_runner = SASTRunner()
        self.secrets_scanner = SecretsScanner()
        self.sbom_generator = SBOMGenerator()
        self.dataflow_analyzer = DataflowAnalyzer()

    @staticmethod
    def fingerprint_finding(finding: dict) -> str:
        raw = (
            f"{finding.get('file_path', '')}:"
            f"{finding.get('line_start', finding.get('line_number', 0))}:"
            f"{finding.get('rule_id', finding.get('secret_type', ''))}:"
            f"{finding.get('code_snippet', finding.get('masked_value', ''))}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    async def process_repo(
        self,
        input: SCRAgentInput,
        detection: dict,
    ) -> RepoScanResult:
        """Run heavy repo-level scanners once (Stages 3–5)."""
        result = RepoScanResult()
        repo_path = input.archive_path
        if not repo_path:
            return result

        languages = set(detection.get("languages", []))
        frameworks = detection.get("frameworks", [])
        semgrep_configs = detection.get("semgrep_configs", ["p/default"])

        tasks = []
        labels = []

        tasks.append(
            self.sast_runner.run_repo(
                repo_path,
                semgrep_configs=semgrep_configs,
                languages=languages,
                frameworks=frameworks,
            )
        )
        labels.append("sast")

        if input.enable_secrets:
            tasks.append(self.secrets_scanner.run_repo(repo_path))
            labels.append("secrets")

        if input.enable_sbom:
            tasks.append(self.sbom_generator.run_repo(repo_path))
            labels.append("sbom")

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for label, res in zip(labels, results):
            if isinstance(res, Exception):
                logger.error("Repo scan %s failed: %s", label, res)
                result.errors.append(f"{label}: {res}")
                continue
            if label == "sast":
                findings, tools = res
                result.code_findings.extend(findings)
                result.tools_invoked.extend(tools)
            elif label == "secrets":
                secrets, tools = res
                result.secret_findings.extend(secrets)
                result.tools_invoked.extend(tools)
            elif label == "sbom":
                sbom, deps, tools = res
                result.sbom = sbom
                result.dependency_findings.extend(deps)
                result.tools_invoked.extend(tools)

        for finding in result.code_findings:
            finding["fingerprint"] = self.fingerprint_finding(finding)
        logger.info(
            "Repo scan complete: %d code, %d secrets, %d deps",
            len(result.code_findings),
            len(result.secret_findings),
            len(result.dependency_findings),
        )
        return result

    async def process_batch(
        self,
        batch_id: str,
        files: list[str],
        input: SCRAgentInput,
        rule_sets: dict,
        *,
        language_map: dict[str, str] | None = None,
        repo_code_findings: list[dict] | None = None,
        repo_secret_findings: list[dict] | None = None,
    ) -> BatchResult:
        """Per-batch dataflow + heuristic supplement (Stages 3/4/6)."""
        result = BatchResult(batch_id=batch_id)
        file_set = set(files)

        if input.enable_dataflow:
            try:
                enrichments, taint_findings = await self.dataflow_analyzer.run(
                    files,
                    file_contents=self._load_file_contents(files, input.archive_path),
                    language_map=language_map or {},
                    archive_path=input.archive_path,
                )
                result.dataflow_enrichments = enrichments
                for tf in taint_findings:
                    tf["fingerprint"] = self.fingerprint_finding(tf)
                result.code_findings.extend(taint_findings)
            except Exception as exc:
                logger.error("Batch %s dataflow failed: %s", batch_id, exc)
                result.errors.append(f"dataflow: {exc}")

        try:
            batch_sast = await self.sast_runner.run(
                files,
                rule_sets,
                archive_path=input.archive_path,
                language_map=language_map,
                repo_findings=repo_code_findings,
            )
            for finding in batch_sast:
                finding["fingerprint"] = self.fingerprint_finding(finding)
            result.code_findings.extend(batch_sast)
        except Exception as exc:
            logger.error("Batch %s sast failed: %s", batch_id, exc)
            result.errors.append(f"sast: {exc}")

        if input.enable_secrets:
            try:
                batch_secrets = await self.secrets_scanner.run(files, archive_path=input.archive_path)
                if repo_secret_findings:
                    batch_secrets.extend(
                        s for s in repo_secret_findings if s.get("file_path") in file_set
                    )
                result.secret_findings = batch_secrets
            except Exception as exc:
                logger.error("Batch %s secrets failed: %s", batch_id, exc)
                result.errors.append(f"secrets: {exc}")

        return result

    @staticmethod
    def _load_file_contents(files: list[str], archive_path: str | None) -> dict[str, str]:
        contents: dict[str, str] = {}
        for file_path in files:
            text = read_repo_file(file_path, archive_path)
            if text:
                contents[file_path] = text
        return contents

    @staticmethod
    def merge_dataflow_enrichments(findings: list[dict], enrichments: list[dict]) -> None:
        by_path = {e["file_path"]: e for e in enrichments}
        for finding in findings:
            path = finding.get("file_path")
            if path not in by_path:
                continue
            enrichment = by_path[path]
            finding["data_flow"] = enrichment.get("data_flow", [])
            finding["reachable_from"] = enrichment.get("reachable_from", [])
