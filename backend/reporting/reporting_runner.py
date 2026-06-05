"""Reporting agent — executive summary from SCR + CMA outputs."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from backend.config.settings import Settings, settings
from backend.infrastructure.model_router import ModelRouter, TaskType
from backend.memory.shared_memory import AgentOutputNotReady, SharedMemoryClient

logger = logging.getLogger(__name__)


def _coerce_findings(raw: object) -> list[dict]:
    if isinstance(raw, list):
        return [f for f in raw if isinstance(f, dict)]
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _dedupe_critical_count(*sources: dict) -> int:
    """Count unique CRITICAL findings by finding_id across agent outputs."""
    unique: dict[str, dict] = {}
    for src in sources:
        for finding in _coerce_findings(src.get("top_findings")):
            fid = str(finding.get("finding_id") or "")
            if not fid:
                continue
            unique[fid] = finding
        for finding in _coerce_findings(src.get("code_findings")):
            fid = str(finding.get("finding_id") or "")
            if not fid:
                continue
            unique[fid] = finding
    if not unique:
        return max(int(s.get("critical_count") or 0) for s in sources) if sources else 0
    return sum(1 for f in unique.values() if str(f.get("severity", "")).upper() == "CRITICAL")


class ReportingRunner:
    """Builds the reporting decision surface from upstream agent outputs."""

    def __init__(
        self,
        shared_memory: SharedMemoryClient,
        app_settings: Settings | None = None,
        model_router: ModelRouter | None = None,
    ) -> None:
        self.shared_memory = shared_memory
        self.settings = app_settings or settings
        self.model_router = model_router

    async def run(self, workflow_id: str, client_id: str) -> None:
        scr = await self._read_agent(workflow_id, "scr")
        cma = await self._read_agent(workflow_id, "cma")

        risk_score = max(int(scr.get("risk_score") or 0), int(cma.get("risk_score") or 0))
        highest_severity = str(
            scr.get("highest_severity") or cma.get("highest_severity") or "LOW"
        ).upper()
        critical_count = _dedupe_critical_count(scr, cma)
        secret_count = int(scr.get("secret_findings_count") or 0)
        requires_human = bool(
            scr.get("requires_human_approval")
            or cma.get("requires_human_approval")
            or risk_score >= 80
        )

        executive_summary = await self._build_summary(scr, cma, risk_score, highest_severity)

        await self.shared_memory.write_agent_output(
            workflow_id,
            "reporting",
            {
                "agent_id": "reporting",
                "completed_at": datetime.now(UTC).isoformat(),
                "risk_score": risk_score,
                "highest_severity": highest_severity,
                "requires_human_approval": requires_human,
                "auto_remediation_safe": risk_score < 50,
                "forward_to": [],
                "critical_count": critical_count,
                "secret_findings_count": secret_count,
                "correlated_to_incident": bool(scr.get("correlated_to_incident")),
                "executive_summary": executive_summary,
                "report_status": "COMPLETED",
            },
        )
        logger.info("Reporting completed for workflow %s — risk=%s", workflow_id, risk_score)

    async def _read_agent(self, workflow_id: str, agent_id: str) -> dict:
        try:
            return await self.shared_memory.read_agent_output(workflow_id, agent_id)
        except AgentOutputNotReady:
            return {}

    async def _build_summary(
        self,
        scr: dict,
        cma: dict,
        risk_score: int,
        highest_severity: str,
    ) -> str:
        top_findings = _coerce_findings(scr.get("top_findings"))
        files_discovered = scr.get("files_discovered", 0)
        gaps = cma.get("gaps_identified") or 0

        fallback = (
            f"Code review completed with risk score {risk_score} ({highest_severity}). "
            f"Scanned {files_discovered} files, identified {len(top_findings)} top findings "
            f"and {gaps} compliance gaps."
        )

        if not self.model_router:
            return fallback

        prompt = (
            "Write a 2-sentence executive summary for a security code review report.\n"
            f"Risk score: {risk_score}\n"
            f"Severity: {highest_severity}\n"
            f"Top findings: {json.dumps(top_findings[:5], default=str)}\n"
            f"Compliance gaps: {gaps}\n"
        )
        try:
            return await self.model_router.complete(
                TaskType.EXECUTIVE_NARRATIVE,
                prompt,
                max_tokens=256,
            )
        except Exception:
            logger.warning("LLM executive summary unavailable — using template")
            return fallback
