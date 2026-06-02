"""Decision surface schema read by the orchestrator for routing."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AgentDecisionSurface:
    """Fields the orchestrator reads from shared memory for routing decisions."""

    agent_id: str
    completed_at: datetime
    risk_score: int  # 0–100
    highest_severity: str
    requires_human_approval: bool
    auto_remediation_safe: bool
    forward_to: list[str]
    critical_count: int
    secret_findings_count: int
    correlated_to_incident: bool
    kill_chain_stage: Optional[int] = None
    audit_due_days: Optional[int] = None
