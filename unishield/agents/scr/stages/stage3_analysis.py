"""Stage 3 — parallel analysis worker pool."""

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
class BatchResult:
    """Unified result from a single analysis batch."""

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

    async def process_batch(
        self,
        batch_id: str,
        files: list[str],
        input: SCRAgentInput,
        rule_sets: dict,
        language_map: dict[str, str] | None = None,
    ) -> BatchResult:
        tasks = [
            self.sast_runner.run(
                files,
                rule_sets,
                archive_path=input.archive_path,
                language_map=language_map or {},
            ),
            self.secrets_scanner.run(files, archive_path=input.archive_path)
            if input.enable_secrets
            else asyncio.sleep(0, result=[]),
            self.sbom_generator.run(files) if input.enable_sbom else asyncio.sleep(0, result={}),
            self.dataflow_analyzer.run(
                files,
                file_contents=self._load_file_contents(files, input.archive_path),
                language_map=language_map or {},
            )
            if input.enable_dataflow
            else asyncio.sleep(0, result=[]),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        result = BatchResult(batch_id=batch_id)
        labels = ["sast", "secrets", "sbom", "dataflow"]

        for label, res in zip(labels, results):
            if isinstance(res, Exception):
                logger.error("Batch %s — %s failed: %s", batch_id, label, res)
                result.errors.append(f"{label}: {res}")
                continue
            if label == "sast":
                result.code_findings = res  # type: ignore[assignment]
            elif label == "secrets":
                result.secret_findings = res  # type: ignore[assignment]
            elif label == "sbom":
                result.sbom_components = res.get("components", []) if isinstance(res, dict) else []
            elif label == "dataflow":
                result.dataflow_enrichments = res  # type: ignore[assignment]

        for finding in result.code_findings:
            finding["fingerprint"] = self.fingerprint_finding(finding)

        return result

    @staticmethod
    def _load_file_contents(files: list[str], archive_path: str | None) -> dict[str, str]:
        contents: dict[str, str] = {}
        for file_path in files:
            text = read_repo_file(file_path, archive_path)
            if text:
                contents[file_path] = text
        return contents
