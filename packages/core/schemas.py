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
