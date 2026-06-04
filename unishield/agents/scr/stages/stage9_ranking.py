"""Stage 9 — finding ranking and deduplication."""

from __future__ import annotations

import logging

from unishield.agents.scr.schemas.output_schema import CodeFinding, DependencyFinding, SecretFinding
from unishield.agents.scr.stages.stage3_analysis import AnalysisStage
from unishield.memory.personal_memory import PersonalMemoryClient

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


class RankingStage:
    """Deduplicates and ranks findings by composite risk score."""

    def __init__(self, personal_memory: PersonalMemoryClient) -> None:
        self._memory = personal_memory

    async def run(self, scan_id: str) -> tuple[list[CodeFinding], list[SecretFinding], list[DependencyFinding], dict[str, int]]:
        findings_data = await self._memory.load_all_findings(scan_id)
        seen: set[str] = set()
        unique: list[dict] = []

        for finding in findings_data["code"]:
            if finding.get("suppressed"):
                continue
            fp = finding.get("fingerprint") or AnalysisStage.fingerprint_finding(finding)
            if fp in seen:
                continue
            seen.add(fp)
            await self._memory.add_fingerprint(scan_id, fp)
            unique.append(finding)

        scored = [(self._score(f), f) for f in unique]
        scored.sort(
            key=lambda x: (
                SEVERITY_ORDER.get(x[1].get("severity", "LOW").upper(), 5),
                -x[0],
            )
        )

        code = [self._to_code_finding(f, scan_id) for _, f in scored]
        secrets = [self._to_secret_finding(s) for s in findings_data.get("secrets", [])]
        deps = [self._to_dependency_finding(d) for d in findings_data.get("dependencies", [])]

        category_counts: dict[str, int] = {}
        for f in code:
            cat = f.category or "unknown"
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return code, secrets, deps, category_counts

    def _score(self, finding: dict) -> float:
        cvss = float(finding.get("cvss_score", 0) or 0)
        if cvss == 0:
            sev = finding.get("severity", "LOW").upper()
            cvss = {"CRITICAL": 9.5, "HIGH": 8.0, "MEDIUM": 5.5, "LOW": 3.0}.get(sev, 4.0)
        reachability = 1.0 if finding.get("reachable_from") else 0.3
        crown_jewel = 1.0 if finding.get("crown_jewel_boost") else 0.0
        exploit = 1.0 if finding.get("exploited_in_wild") else 0.2
        risk_boost = min(25, int(finding.get("risk_boost", 0))) / 25.0
        fp_penalty = float(finding.get("false_positive_score", 0))
        return (cvss * 0.3 + reachability * 0.2 + crown_jewel * 0.2 + exploit * 0.15 + risk_boost * 0.15) * (1 - fp_penalty * 0.5)

    def _to_code_finding(self, raw: dict, scan_id: str) -> CodeFinding:
        return CodeFinding(
            finding_id=raw.get("finding_id", ""),
            scan_id=scan_id,
            file_path=raw.get("file_path", ""),
            language=raw.get("language", "unknown"),
            line_start=raw.get("line_start", 0),
            line_end=raw.get("line_end", 0),
            column_start=raw.get("column_start", 0),
            column_end=raw.get("column_end", 0),
            code_snippet=raw.get("code_snippet", ""),
            severity=raw.get("severity", "LOW"),
            confidence=raw.get("confidence", 0.5),
            category=raw.get("category", "unknown"),
            cwe_id=raw.get("cwe_id"),
            mitre_technique=raw.get("mitre_technique"),
            ai_explanation=raw.get("ai_explanation"),
            ai_attack_scenario=raw.get("ai_attack_scenario"),
            ai_business_impact=raw.get("ai_business_impact"),
            ai_fix=raw.get("ai_fix"),
            ai_fix_code=raw.get("ai_fix_code"),
            false_positive_score=raw.get("false_positive_score", 0.0),
            threat_actor_relevance=raw.get("threat_actor_relevance", []),
            incident_relevance=raw.get("incident_relevance", False),
            exploited_in_wild=raw.get("exploited_in_wild", False),
            reachable_from=raw.get("reachable_from", []),
            data_flow=raw.get("data_flow", []),
            suppressed=raw.get("suppressed", False),
            suppression_reason=raw.get("suppression_reason"),
        )

    @staticmethod
    def _to_secret_finding(raw: dict) -> SecretFinding:
        return SecretFinding(
            secret_type=raw.get("secret_type", "secret"),
            file_path=raw.get("file_path", ""),
            line_number=raw.get("line_number", 0),
            masked_value=raw.get("masked_value", "****"),
            entropy_score=float(raw.get("entropy_score", 0)),
            verified_live=raw.get("verified_live", False),
            git_history_exposed=raw.get("git_history_exposed", False),
        )

    @staticmethod
    def _to_dependency_finding(raw: dict) -> DependencyFinding:
        return DependencyFinding(
            package_name=raw.get("package_name", "unknown"),
            version=raw.get("version", "unknown"),
            ecosystem=raw.get("ecosystem", "unknown"),
            cve_id=raw.get("cve_id", "UNKNOWN"),
            cvss_score=float(raw.get("cvss_score", 0)),
            severity=raw.get("severity", "HIGH"),
            fixed_version=raw.get("fixed_version"),
            is_transitive=raw.get("is_transitive", False),
            dependency_path=raw.get("dependency_path", []),
            exploitable=raw.get("exploitable", False),
            exploit_available=raw.get("exploit_available", False),
        )
