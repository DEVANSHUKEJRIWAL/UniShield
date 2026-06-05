"""Shared agent output contract for Kafka and shared memory."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AgentOutputEnvelope:
    """Contract every agent writes to Kafka and shared memory."""

    agent_id: str
    agent_version: str
    timestamp: datetime
    correlation_id: str
    client_id: str
    payload_type: str
    payload: dict
    severity: str  # CRITICAL / HIGH / MEDIUM / LOW
    requires_human_review: bool
    forwarded_to: list[str] = field(default_factory=list)
    incident_id: Optional[str] = None
