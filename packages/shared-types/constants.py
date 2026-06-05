"""Shared constants for UniShield platform."""

from enum import StrEnum


class RedisStream(StrEnum):
    """Redis Streams key naming conventions."""

    EVENTS_RAW = "unishield:events:raw"
    HITL_QUEUE = "unishield:hitl:queue"
    AUDIT_LOG = "unishield:audit:log"


class UserRole(StrEnum):
    """RBAC role definitions."""

    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    CLIENT_ADMIN = "CLIENT_ADMIN"
    CISO = "CISO"
    SOC_ANALYST = "SOC_ANALYST"
    READONLY_BOARD = "READONLY_BOARD"
    DEVSECOPS = "DEVSECOPS"
    GRC = "GRC"


class AgentName(StrEnum):
    """Workflow agent identifiers (orchestrator pipeline)."""

    ORCHESTRATOR = "orchestrator"
    SOURCE_CODE = "source-code-agent"
    COMPLIANCE = "compliance-agent"
    REPORTING = "reporting-agent"
