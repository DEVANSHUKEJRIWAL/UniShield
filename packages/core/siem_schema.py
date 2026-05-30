"""SIEM integration normalised event schema (Week 4)."""

from typing import Any

from pydantic import BaseModel, Field


class SiemNormalizedEvent(BaseModel):
    """Normalised event from Splunk/QRadar/Sentinel connectors."""

    event_id: str
    tenant_id: str
    source: str  # splunk | qradar | sentinel
    type: str = "siem_alert"
    severity: str = "medium"
    timestamp: str
    raw: dict[str, Any] = Field(default_factory=dict)
    iocs: list[dict[str, str]] = Field(default_factory=list)
    mitre_ttps: list[str] = Field(default_factory=list)
    query: str | None = None

    def to_agent_event(self) -> dict[str, Any]:
        """Convert to orchestrator-compatible event payload."""
        return {
            "event_id": self.event_id,
            "tenant_id": self.tenant_id,
            "type": "siem_alert",
            "source": self.source,
            "severity": self.severity,
            "payload": self.raw,
            "iocs": self.iocs,
            "mitre_ttps": self.mitre_ttps,
            "query": self.query,
        }
