"""Stage 10 — output assembly and shared memory write."""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import UTC, datetime

from unishield.agents.scr.schemas.input_schema import SCRAgentInput
from unishield.agents.scr.schemas.output_schema import CodeFinding, SCRAgentOutput
from unishield.infrastructure.kafka_client import KafkaClient
from unishield.memory.personal_memory import PersonalMemoryClient
from unishield.memory.shared_memory import SharedMemoryClient

logger = logging.getLogger(__name__)


class OutputStage:
    """Builds final output, writes to shared memory, and emits completion event."""

    def __init__(
        self,
        personal_memory: PersonalMemoryClient,
        shared_memory: SharedMemoryClient,
        kafka: KafkaClient,
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
        input: SCRAgentInput,
        started_at: datetime,
        files_scanned: int,
    ) -> SCRAgentOutput:
        findings_data = await self._memory.load_all_findings(scan_id)
        completed_at = datetime.now(UTC)
        duration = (completed_at - started_at).total_seconds()

        severity_counts: dict[str, int] = {}
        for f in ranked_findings:
            sev = f.severity.upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        risk_score = min(100, severity_counts.get("CRITICAL", 0) * 30 + severity_counts.get("HIGH", 0) * 15 + len(findings_data["secrets"]) * 20)
        risk_label = "CRITICAL" if risk_score >= 80 else "HIGH" if risk_score >= 50 else "MEDIUM" if risk_score >= 25 else "LOW"

        output = SCRAgentOutput(
            scan_id=scan_id,
            request_id=input.request_id,
            client_id=input.client_id,
            scan_mode=input.scan_mode.value,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            scan_status="COMPLETED",
            files_discovered=files_scanned,
            files_scanned=files_scanned,
            files_skipped=0,
            lines_analyzed=files_scanned * 100,
            languages_detected=[],
            risk_score=risk_score,
            risk_label=risk_label,
            total_findings=len(ranked_findings) + len(findings_data["secrets"]),
            findings_by_severity=severity_counts,
            findings_by_category={},
            code_findings=ranked_findings,
            dependency_findings=[],
            secret_findings=[],
            sbom={},
            sbom_summary={"components": 0},
            executive_summary=f"Scan completed with risk score {risk_score}",
            technical_summary=f"Found {len(ranked_findings)} code findings",
            top_risks=[f.file_path for f in ranked_findings[:5]],
            remediation_plan=["Review and fix critical findings"],
            compliance_gaps=[],
            frameworks_assessed=input.frameworks,
            agent_version=self._version,
            models_used=[input.enable_ai_analysis and "claude-sonnet" or ""],
            tools_invoked=["sast", "secrets", "sbom", "dataflow"],
            forwarded_to=[],
        )

        decision_surface = {
            "agent_id": "UniShield-SCR",
            "completed_at": completed_at.isoformat(),
            "risk_score": risk_score,
            "highest_severity": risk_label,
            "requires_human_approval": risk_score >= 80,
            "auto_remediation_safe": risk_score < 50,
            "forward_to": [],
            "critical_count": severity_counts.get("CRITICAL", 0),
            "secret_findings_count": len(findings_data["secrets"]),
            "correlated_to_incident": bool(input.active_incident_id),
            "kill_chain_stage": None,
            "audit_due_days": None,
            "top_findings": [asdict(f) for f in ranked_findings[:10]],
            "sbom": output.sbom,
        }

        await self._shared.write_agent_output(input.workflow_id, "UniShield-SCR", decision_surface)

        await self._kafka.publish(
            "agent.complete",
            {
                "workflow_id": input.workflow_id,
                "agent_id": "UniShield-SCR",
                "client_id": input.client_id,
                "correlation_id": input.correlation_id or input.workflow_id,
                "status": "SUCCESS",
                "completed_at": completed_at.isoformat(),
            },
            key=input.workflow_id,
        )

        await self._memory.expire_all(scan_id)
        logger.info("Output stage complete for scan %s", scan_id)
        return output
