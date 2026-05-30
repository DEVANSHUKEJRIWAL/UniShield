"""Insider threat data schema (Week 3)."""

from pydantic import BaseModel, Field


class UserBaseline(BaseModel):
    """Behavioural baseline for UEBA."""

    user_id: str
    tenant_id: str
    peer_group: str = "default"
    window30d: dict[str, float] = Field(default_factory=lambda: {"avg_logins": 12.0, "avg_data_volume_mb": 450.0})
    window60d: dict[str, float] = Field(default_factory=lambda: {"avg_logins": 11.0, "avg_data_volume_mb": 420.0})


class AccessEvent(BaseModel):
    """Normalised access log event."""

    user_id: str
    action: str
    resource: str
    timestamp: str
    source_ip: str | None = None
    success: bool = True


class InsiderRiskScore(BaseModel):
    """Insider threat agent output."""

    user_id: str
    z_score: float
    anomalous: bool
    peer_group: str
    severity: str = "medium"
    confidence: float = Field(ge=0.0, le=1.0, default=0.75)
    factors: list[str] = Field(default_factory=list)
