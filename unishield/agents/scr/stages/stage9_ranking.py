"""Stage 9 — finding ranking and deduplication."""

from __future__ import annotations

import logging

from unishield.agents.scr.schemas.output_schema import CodeFinding
from unishield.agents.scr.stages.stage3_analysis import AnalysisStage
from unishield.memory.personal_memory import PersonalMemoryClient

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


class RankingStage:
    """Deduplicates and ranks findings by composite risk score."""

    def __init__(self, personal_memory: PersonalMemoryClient) -> None:
        self._memory = personal_memory

    async def run(self, scan_id: str) -> list[CodeFinding]:
        findings_data = await self._memory.load_all_findings(scan_id)
        seen: set[str] = set()
        unique: list[dict] = []

        for finding in findings_data["code"]:
            fp = finding.get("fingerprint") or AnalysisStage.fingerprint_finding(finding)
            if fp in seen:
                continue
            seen.add(fp)
            await self._memory.add_fingerprint(scan_id, fp)
            unique.append(finding)

        scored = [(self._score(f), f) for f in unique]
        scored.sort(key=lambda x: (SEVERITY_ORDER.get(x[1].get("severity", "LOW").upper(), 4), -x[0]))

        return [self._to_code_finding(f, scan_id) for _, f in scored]

    def _score(self, finding: dict) -> float:
        cvss = float(finding.get("cvss_score", 5.0))
        reachability = 1.0 if finding.get("reachable_from") else 0.3
        crown_jewel = 1.0 if finding.get("crown_jewel_boost") else 0.0
        exploit = 1.0 if finding.get("exploited_in_wild") else 0.2
        return cvss * 0.3 + reachability * 0.25 + crown_jewel * 0.25 + exploit * 0.2

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
            threat_actor_relevance=raw.get("threat_actor_relevance", []),
            incident_relevance=raw.get("incident_relevance", False),
            exploited_in_wild=raw.get("exploited_in_wild", False),
            reachable_from=raw.get("reachable_from", []),
        )
