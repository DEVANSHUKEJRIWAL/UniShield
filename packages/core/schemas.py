"""Structured finding output schemas for all agents."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConfidenceBreakdown(BaseModel):
    """Per-dimension confidence scores."""

    detection: float = Field(ge=0.0, le=1.0, default=0.8)
    evidence_quality: float = Field(ge=0.0, le=1.0, default=0.8)
    context_completeness: float = Field(ge=0.0, le=1.0, default=0.7)


class AgentFinding(BaseModel):
    """Standard agent finding output — all agents emit this structure."""

    finding_id: str
    tenant_id: str
    agent_id: str
    type: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    confidence: float = Field(ge=0.0, le=1.0)
    title: str
    description: str
    reasoning_summary: str = Field(max_length=2000)
    evidence_references: list[str] = Field(default_factory=list)
    confidence_breakdown: ConfidenceBreakdown = Field(default_factory=ConfidenceBreakdown)
    mitre_ttps_matched: list[str] = Field(default_factory=list)
    contributing_agents: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    hitl_required: bool = False
    raw: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"strict": True}


class BreachFinding(AgentFinding):
    """Dark web agent finding."""

    type: str = "breach"
    affected_entities: list[str] = Field(default_factory=list)


class CodeFinding(AgentFinding):
    """Source code review finding."""

    type: str = "code"
    file_path: str = ""
    line_number: int = 0
    cwe_reference: str = ""
    recommended_fix: str = ""


class IRFinding(AgentFinding):
    """Incident response finding."""

    type: str = "incident_response"
    playbook_reference: str = ""
    priority_actions: list[str] = Field(default_factory=list)


class ForensicFinding(AgentFinding):
    """Forensics agent finding."""

    type: str = "forensics"
    iocs: list[dict[str, str]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    kg_entity_links: list[str] = Field(default_factory=list)


class CredentialExposureAlert(BaseModel):
    """Week 2 credential alert schema — dark web / breach feed normalisation."""

    domain: str
    exposed_count: int = 0
    latest_breach: str | None = None
    severity: Literal["critical", "high", "medium", "low"] = "high"
    confidence: float = Field(ge=0.0, le=1.0, default=0.85)
    source: str = "breach_intel"
    affected_identities: list[str] = Field(default_factory=list)
    summary: str = ""

    @classmethod
    def from_tool_result(cls, data: dict[str, Any]) -> "CredentialExposureAlert":
        """Build alert from check_credential_exposure tool output."""
        count = int(data.get("exposed_count", 0))
        severity = data.get("severity", "high")
        if severity not in ("critical", "high", "medium", "low"):
            severity = "high"
        domain = str(data.get("domain", "unknown"))
        return cls(
            domain=domain,
            exposed_count=count,
            latest_breach=data.get("latest_breach"),
            severity=severity,
            confidence=min(0.95, 0.6 + count * 0.005),
            source=str(data.get("source", "breach_intel")),
            affected_identities=[f"user@{domain}" for _ in range(min(count, 3))],
            summary=data.get("summary")
            or (
                f"{count} credentials exposed for {domain}"
                + (f" (latest breach: {data.get('latest_breach')})" if data.get("latest_breach") else "")
            ),
        )
