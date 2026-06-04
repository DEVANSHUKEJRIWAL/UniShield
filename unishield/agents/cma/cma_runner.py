"""Compliance mapping agent — derives CMA output from SCR findings."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from unishield.config.settings import Settings, settings
from unishield.infrastructure.model_router import ModelRouter, TaskType
from unishield.memory.shared_memory import AgentOutputNotReady, SharedMemoryClient

logger = logging.getLogger(__name__)

PCI_CONTROLS = {
    "code_execution": "6.2.4",
    "command_injection": "6.2.4",
    "injection": "6.5.1",
    "secrets": "8.2.1",
    "crypto": "3.5.1",
}


class CMARunner:
    """Maps SCR findings to compliance posture and writes the CMA decision surface."""

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
        try:
            scr = await self.shared_memory.read_agent_output(workflow_id, "scr")
        except AgentOutputNotReady as exc:
            raise RuntimeError("CMA requires SCR output in shared memory") from exc

        top_findings = scr.get("top_findings") or []
        if isinstance(top_findings, str):
            top_findings = json.loads(top_findings) if top_findings else []

        risk_score = int(scr.get("risk_score") or 0)
        highest_severity = str(scr.get("highest_severity") or "LOW").upper()
        critical_count = int(scr.get("critical_count") or 0)
        secret_count = int(scr.get("secret_findings_count") or 0)

        compliance_gaps = self._map_compliance_gaps(top_findings, secret_count)
        if self.model_router and top_findings:
            compliance_gaps = await self._enrich_with_llm(top_findings, compliance_gaps)

        requires_human = risk_score >= 80 or highest_severity in ("CRITICAL", "HIGH") and secret_count > 0

        await self.shared_memory.write_agent_output(
            workflow_id,
            "cma",
            {
                "agent_id": "cma",
                "completed_at": datetime.now(UTC).isoformat(),
                "risk_score": risk_score,
                "highest_severity": highest_severity,
                "requires_human_approval": requires_human,
                "auto_remediation_safe": risk_score < 50,
                "forward_to": [],
                "critical_count": critical_count,
                "secret_findings_count": secret_count,
                "correlated_to_incident": bool(scr.get("correlated_to_incident")),
                "compliance_gaps": compliance_gaps,
                "frameworks_assessed": ["PCI-DSS", "SOC2", "ISO27001"],
                "gaps_identified": len(compliance_gaps),
            },
        )
        logger.info(
            "CMA completed for workflow %s — risk=%s gaps=%d",
            workflow_id,
            risk_score,
            len(compliance_gaps),
        )

    def _map_compliance_gaps(self, findings: list, secret_count: int) -> list[dict]:
        gaps: list[dict] = []
        seen: set[str] = set()
        for finding in findings:
            category = str(finding.get("category") or "unknown")
            control = PCI_CONTROLS.get(category, "6.2.4")
            key = f"{control}:{category}"
            if key in seen:
                continue
            seen.add(key)
            gaps.append(
                {
                    "framework": "PCI-DSS",
                    "control": control,
                    "category": category,
                    "severity": finding.get("severity", "MEDIUM"),
                    "file_path": finding.get("file_path"),
                    "status": "FAIL",
                }
            )
        if secret_count > 0 and "secrets" not in seen:
            gaps.append(
                {
                    "framework": "PCI-DSS",
                    "control": PCI_CONTROLS["secrets"],
                    "category": "secrets",
                    "severity": "HIGH",
                    "status": "FAIL",
                    "details": f"{secret_count} secret(s) detected in repository",
                }
            )
        return gaps

    async def _enrich_with_llm(self, findings: list, gaps: list[dict]) -> list[dict]:
        if not self.model_router:
            return gaps
        prompt = (
            "Given these code security findings, list up to 5 compliance gaps as JSON array "
            'with keys framework, control, category, severity, status. Findings:\n'
            f"{json.dumps(findings[:10], default=str)}"
        )
        try:
            text = await self.model_router.complete(
                TaskType.COMPLIANCE_MAPPING,
                prompt,
                max_tokens=1024,
            )
            parsed = json.loads(text)
            if isinstance(parsed, list) and parsed:
                return parsed
        except Exception:
            logger.warning("LLM compliance enrichment unavailable — using heuristic gaps")
        return gaps
