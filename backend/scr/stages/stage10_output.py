"""Stage 10 — output assembly, shared memory, and Kafka signalling."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from backend.scr.schemas.input_schema import SCRAgentInput
from backend.scr.schemas.output_schema import (
    CodeFinding,
    DependencyFinding,
    SCRAgentOutput,
    SecretFinding,
)
from backend.scr.stages.findings_filter import FilterStats
from backend.scr.tools.scanner_integration import sbom_summary
from backend.infrastructure.kafka_client import KafkaProducer
from backend.memory.personal_memory import PersonalMemoryClient
from backend.memory.shared_memory import SharedMemoryClient

logger = logging.getLogger(__name__)


class OutputStage:
    """Builds final SCRAgentOutput, writes shared memory, emits completion event."""

    def __init__(
        self,
        personal_memory: PersonalMemoryClient,
        shared_memory: SharedMemoryClient,
        kafka: KafkaProducer,
        agent_version: str,
    ) -> None:
        self._memory = personal_memory
        self._shared = shared_memory
        self._kafka = kafka
        self._version = agent_version

    async def run(
        self,
        scan_id: str,
        ranked_findings: list[CodeFinding],
        secret_findings: list[SecretFinding],
        dependency_findings: list[DependencyFinding],
        input: SCRAgentInput,
        started_at: datetime,
        *,
        files_discovered: int,
        files_scanned: int,
        languages_detected: list[str],
        frameworks_detected: list[str],
        sbom: dict,
        tools_invoked: list[str],
        models_used: list[str],
        category_counts: dict[str, int],
        threat_intel_boost: int,
        attack_summary: dict,
        filter_stats: FilterStats | None = None,
        ai_filter_enabled: bool = False,
        scan_status: str = "COMPLETED",
        error_message: str | None = None,
    ) -> SCRAgentOutput:
        completed_at = datetime.now(UTC)
        duration = (completed_at - started_at).total_seconds()
        stats = filter_stats or FilterStats()

        severity_counts: dict[str, int] = {}
        for f in ranked_findings:
            sev = f.severity.upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        dep_high = sum(1 for d in dependency_findings if d.cvss_score >= 7.0)
        risk_score = min(
            100,
            severity_counts.get("CRITICAL", 0) * 30
            + severity_counts.get("HIGH", 0) * 15
            + len(secret_findings) * 20
            + dep_high * 10
            + min(threat_intel_boost, 50),
        )
        risk_label = (
            "CRITICAL" if risk_score >= 80 else "HIGH" if risk_score >= 50 else "MEDIUM" if risk_score >= 25 else "LOW"
        )

        top_risks = [f"{f.severity}: {f.file_path}:{f.line_start} ({f.category})" for f in ranked_findings[:5]]
        remediation_plan = self._build_remediation_plan(ranked_findings, secret_findings, dependency_findings)
        compliance_gaps = self._compliance_gaps(ranked_findings, input.frameworks)
        exec_summary = (
            f"Scan completed with risk score {risk_score} ({risk_label}). "
            f"{len(ranked_findings)} code findings, {len(secret_findings)} secrets, "
            f"{len(dependency_findings)} dependency issues (CVSS≥7)."
        )
        tech_summary = (
            f"Tools: {', '.join(sorted(set(tools_invoked))) or 'heuristic'}. "
            f"Languages: {', '.join(languages_detected) or 'unknown'}. "
            f"Frameworks: {', '.join(frameworks_detected) or 'none detected'}."
        )

        summary = sbom_summary(sbom)
        output = SCRAgentOutput(
            scan_id=scan_id,
            request_id=input.request_id,
            client_id=input.client_id,
            scan_mode=str(input.scan_mode),
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            scan_status=scan_status,
            files_discovered=files_discovered,
            files_scanned=files_scanned,
            files_skipped=max(0, files_discovered - files_scanned),
            lines_analyzed=files_scanned * 100,
            languages_detected=languages_detected,
            risk_score=risk_score,
            risk_label=risk_label,
            total_findings=len(ranked_findings) + len(secret_findings) + len(dependency_findings),
            findings_by_severity=severity_counts,
            findings_by_category=category_counts,
            code_findings=ranked_findings,
            dependency_findings=dependency_findings,
            secret_findings=secret_findings,
            sbom=sbom,
            sbom_summary=summary,
            executive_summary=exec_summary,
            technical_summary=tech_summary,
            top_risks=top_risks,
            remediation_plan=remediation_plan,
            compliance_gaps=compliance_gaps,
            frameworks_assessed=frameworks_detected or input.frameworks,
            agent_version=self._version,
            models_used=[m for m in models_used if m],
            tools_invoked=sorted(set(tools_invoked)),
            correlated_findings=[
                f.finding_id for f in ranked_findings if f.incident_relevance or f.threat_actor_relevance
            ],
            forwarded_to=[],
        )

        payload: dict = {
            "agent_id": "scr",
            "completed_at": completed_at.isoformat(),
            "risk_score": risk_score,
            "highest_severity": risk_label,
            "requires_human_approval": risk_score >= 80,
            "auto_remediation_safe": risk_score < 50,
            "forward_to": [],
            "critical_count": severity_counts.get("CRITICAL", 0),
            "secret_findings_count": len(secret_findings),
            "dependency_findings_count": len(dependency_findings),
            "correlated_to_incident": bool(input.active_incident_id),
            "top_findings": [f.model_dump() for f in ranked_findings[:10]],
            "code_findings": [f.model_dump() for f in ranked_findings],
            "secret_findings": [s.model_dump() for s in secret_findings[:20]],
            "dependency_findings": [d.model_dump() for d in dependency_findings[:20]],
            "sbom_summary": summary,
            "sbom": sbom,
            "compliance_gaps": compliance_gaps,
            "remediation_plan": remediation_plan,
            "attack_paths_summary": attack_summary,
            "scan_status": scan_status,
            "files_discovered": files_discovered,
            "total_findings": output.total_findings,
            "analysis_stats": {
                "sast_raw": stats.total_input,
                "sast_kept": stats.kept,
                "hard_excluded": stats.hard_excluded,
                "ai_excluded": stats.ai_excluded,
                "ai_filter_enabled": ai_filter_enabled,
                "secret_findings": len(secret_findings),
                "dependency_findings": len(dependency_findings),
                "tools_invoked": output.tools_invoked,
            },
        }
        if error_message:
            payload["error_message"] = error_message

        await self._shared.write_agent_output(input.workflow_id, "scr", payload)

        if scan_status == "COMPLETED":
            await self._kafka.publish(
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
            await self._memory.expire_all(scan_id)

        logger.info("Output stage complete for scan %s (risk=%d)", scan_id, risk_score)
        return output

    @staticmethod
    def _build_remediation_plan(
        code: list[CodeFinding],
        secrets: list[SecretFinding],
        deps: list[DependencyFinding],
    ) -> list[str]:
        plan: list[str] = []
        if any(f.severity.upper() == "CRITICAL" for f in code):
            plan.append("Prioritize CRITICAL code findings — patch or mitigate within 24 hours.")
        if secrets:
            plan.append("Rotate exposed credentials and purge secrets from git history.")
        if deps:
            plan.append("Upgrade dependencies with CVSS ≥ 7.0 to fixed versions.")
        for f in code[:5]:
            if f.ai_fix:
                plan.append(f"{f.file_path}: {f.ai_fix}")
        if not plan:
            plan.append("Review findings and apply secure coding standards.")
        return plan

    @staticmethod
    def _compliance_gaps(code: list[CodeFinding], frameworks: list[str]) -> list[str]:
        gaps: list[str] = []
        if any(f.cwe_id == "CWE-89" for f in code):
            gaps.append("PCI-DSS 6.5.1 — Injection flaws in application code")
        if any(f.category == "secrets" or "secret" in f.category for f in code):
            gaps.append("PCI-DSS 8.2 — Credential and secret management")
        if any("xss" in f.category for f in code):
            gaps.append("OWASP A03:2021 — Injection / XSS")
        for fw in frameworks:
            gaps.append(f"{fw.upper()} security baseline review required")
        return gaps
