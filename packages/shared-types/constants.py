"""Shared constants for UniShield platform."""

from enum import StrEnum


class RedisStream(StrEnum):
    """Redis Streams key naming conventions."""

    EVENTS_RAW = "unishield:events:raw"
    EVENTS_NORMALISED = "unishield:events:normalised"
    HITL_QUEUE = "unishield:hitl:queue"
    RISK_SCORES = "unishield:risk:scores"
    AUDIT_LOG = "unishield:audit:log"

    @staticmethod
    def priority_queue(priority: str) -> str:
        """Return priority queue stream key (Week 2)."""
        return f"unishield:queue:{priority.lower()}"

    @staticmethod
    def agent_tasks(agent_name: str) -> str:
        """Return agent task stream key."""
        return f"unishield:agent:{agent_name}:tasks"

    @staticmethod
    def agent_findings(agent_name: str) -> str:
        """Return agent findings stream key."""
        return f"unishield:agent:{agent_name}:findings"

    @staticmethod
    def events_raw(source_type: str) -> str:
        """Return raw events stream key for a source type."""
        return f"unishield:events:raw:{source_type}"


class QdrantCollection(StrEnum):
    """Qdrant vector store collections."""

    THREAT_INTEL = "threat_intel"
    CVE_DESCRIPTIONS = "cve_descriptions"
    IR_PLAYBOOKS = "ir_playbooks"
    INSIDER_PATTERNS = "insider_patterns"
    DARK_WEB_CORPUS = "dark_web_corpus"


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
    """Registered agent identifiers."""

    ORCHESTRATOR = "orchestrator"
    DARK_WEB = "dark-web-agent"
    SOURCE_CODE = "source-code-agent"
    INSIDER_THREAT = "insider-threat-agent"
    THREAT_INTEL = "threat-intel-agent"
    VULNERABILITY = "vulnerability-agent"
    INCIDENT_RESPONSE = "incident-response-agent"
    SIEM_ANALYSIS = "siem-analysis-agent"
    NETWORK_SECURITY = "network-security-agent"
    COMPLIANCE = "compliance-agent"
    FORENSICS = "forensics-agent"
    GRAPH_QUERY = "graph-query-agent"
    REPORTING = "reporting-agent"
