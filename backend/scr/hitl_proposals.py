"""Propose HITL review actions for critical SCR findings."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from backend.orchestrator.action_gate import ActionGate
from backend.schemas.action_contract import ActionScope, ProposedAction


async def propose_finding_reviews(
    action_gate: ActionGate,
    *,
    workflow_id: str,
    findings: list[dict[str, Any]],
    risk_score: int,
) -> list[str]:
    """Register human-review actions for critical/high findings."""
    proposed: list[str] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        severity = str(finding.get("severity", "")).upper()
        if severity not in ("CRITICAL", "HIGH") and risk_score < 80:
            continue
        finding_id = str(finding.get("finding_id") or uuid.uuid4())
        action_id = f"HITL-{workflow_id}-{finding_id[:12]}"
        description = json.dumps(
            {
                "title": f"{finding.get('category', 'Finding')}: {finding.get('file_path', 'unknown')}",
                "severity": severity.lower(),
                "finding_id": finding_id,
                "file_path": finding.get("file_path"),
                "line_start": finding.get("line_start"),
                "cwe_id": finding.get("cwe_id"),
                "reasoning": finding.get("description") or finding.get("ai_rationale"),
                "confidence": finding.get("confidence", 0.9),
                "priority": "P1" if severity == "CRITICAL" else "P2",
            }
        )
        action = ProposedAction(
            action_id=action_id,
            workflow_id=workflow_id,
            agent_id="unishield-scr",
            action_type="remediation_review",
            scope=ActionScope.WRITE_SCOPE,
            target=str(finding.get("file_path") or workflow_id),
            description=description,
            impact=f"Review required before remediation of {severity} finding in {finding.get('file_path')}",
            reversible=True,
            proposed_at=datetime.now(UTC),
            rollback_steps="Revert applied remediation if rejected during review.",
        )
        proposed.append(await action_gate.propose(action))
    return proposed
