"""HITL service — human-in-the-loop decision queue."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class HITLDecision(StrEnum):
    """Analyst decision options."""

    ACCEPT = "accept"
    MODIFY = "modify"
    REJECT = "reject"


class HITLRequest(BaseModel):
    """Agent-proposed action requiring human approval."""

    action_id: str
    tenant_id: str
    agent_id: str
    action: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    evidence: list[str] = Field(default_factory=list)
    expiry_ts: datetime
    severity: str = "medium"

    model_config = {"strict": True}


def should_require_hitl(confidence: float, risk_level: str, severity: str) -> bool:
    """
    HITL policy — confidence × risk thresholds (§11).
    Returns True if human approval is required.
    """
    if severity.upper() == "CRITICAL":
        return True
    if confidence < 0.80:
        return True
    if confidence >= 0.95 and risk_level.upper() == "LOW":
        return False
    if confidence >= 0.90 and risk_level.upper() == "MEDIUM":
        return True
    if confidence >= 0.80 and risk_level.upper() == "HIGH":
        return True
    return True
