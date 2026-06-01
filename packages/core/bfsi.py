"""BFSI finding schema helpers (Phase 2 — Dark Web, Source Code, Insider)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

BFSIKind = Literal[
    "leaked-credential",
    "paste-leak",
    "threat-actor-mention",
    "brand-mention",
    "typosquat-domain",
    "code-vulnerability",
    "insider-threat",
]

DataMode = Literal["live", "mock-fallback", "mock-phase-1"]

INDUSTRY_REGULATORS: dict[str, list[str]] = {
    "banking": ["RBI Cyber Resilience Framework", "DORA Art.9", "PCI-DSS 12.6", "DPDP Act 2023"],
    "pharma": ["DORA Art.9", "FDA 21 CFR Part 11", "DPDP Act 2023"],
    "healthcare": ["HIPAA Security Rule", "DPDP Act 2023", "DORA Art.10"],
    "energy": ["NERC CIP", "DORA Art.9", "IEC 62443"],
    "default": ["DORA Art.9", "NIST CSF", "DPDP Act 2023"],
}


class BFSIFinding(BaseModel):
    """Universal BFSI finding shape (Phase 2 portal + agents)."""

    id: str
    agentId: str
    kind: str
    severity: Literal["critical", "high", "medium", "low"]
    confidence: Literal["high", "medium", "low"]
    title: str
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    asset: str = ""
    feedSource: str = ""
    remediation: str = ""
    regulators: list[str] = Field(default_factory=list)
    detectedAt: str = ""
    dataMode: DataMode = "live"
    riskScore: int | None = None

    def to_agent_finding_raw(self) -> dict[str, Any]:
        """Embed in AgentFinding.raw for persistence."""
        return self.model_dump()


_CONFIDENCE_SCORE = {"high": 0.9, "medium": 0.75, "low": 0.6}


def bfsi_to_agent_finding(
    bfsi: BFSIFinding,
    tenant_id: str,
    agent_id: str,
    *,
    finding_type: str | None = None,
) -> "AgentFinding":
    """Convert BFSI finding to standard AgentFinding for persistence."""
    from packages.core.schemas import AgentFinding

    return AgentFinding(
        finding_id=bfsi.id,
        tenant_id=tenant_id,
        agent_id=agent_id,
        type=finding_type or bfsi.kind,
        severity=bfsi.severity,
        confidence=_CONFIDENCE_SCORE.get(bfsi.confidence, 0.75),
        title=bfsi.title,
        description=bfsi.description,
        reasoning_summary=f"Phase 2 scan via {bfsi.feedSource} ({bfsi.dataMode})",
        evidence_references=[bfsi.asset] if bfsi.asset else [],
        recommended_actions=[bfsi.remediation] if bfsi.remediation else [],
        contributing_agents=[agent_id],
        raw=bfsi.to_agent_finding_raw(),
    )


def stable_bfsi_id(prefix: str, *parts: str) -> str:
    """Stable dedupe-friendly finding id."""
    digest = hashlib.sha256(":".join(parts).encode()).hexdigest()[:12]
    return f"{prefix}-{digest}"


def regulators_for_industry(industry: str) -> list[str]:
    key = (industry or "default").lower().strip()
    return list(INDUSTRY_REGULATORS.get(key, INDUSTRY_REGULATORS["default"]))


def confidence_label(score: float) -> Literal["high", "medium", "low"]:
    if score >= 0.85:
        return "high"
    if score >= 0.65:
        return "medium"
    return "low"


def severity_from_risk_score(score: int) -> Literal["critical", "high", "medium", "low"]:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
