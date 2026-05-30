"""Normalised event schema for UniShield platform."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class NormalisedEvent(BaseModel):
    """Unified security event envelope — all platform events must conform."""

    event_id: str = Field(description="UUID v4")
    tenant_id: str = Field(description="Client ID — multi-tenant isolation key")
    source_type: str = Field(description="siem | edr | iam | cloud | osint | code | itsm | network")
    source_vendor: str = Field(description="splunk | crowdstrike | okta | guardduty | github | etc.")
    timestamp: datetime = Field(description="UTC ISO-8601")
    severity: Literal["critical", "high", "medium", "low", "info"]
    category: str = Field(description="auth | process | network | file | cloud | code | identity")
    entity_type: str = Field(description="user | device | service | repo | cloud_resource | ip")
    entity_id: str = Field(description="Resolved entity ID mapped to KG node")
    raw: dict = Field(description="Original vendor payload (immutable)")
    mitre_ttps: list[str] = Field(default_factory=list, description="MITRE ATT&CK technique IDs")
    cvss_tags: list[str] = Field(default_factory=list, description="Relevant CVE IDs")
    geo_ip: dict | None = None
    schema_version: str = "1.0"

    model_config = {"strict": True}
