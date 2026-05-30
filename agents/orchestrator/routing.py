"""Orchestrator event routing (Week 2)."""

from typing import Any

from packages.shared_types.constants import AgentName

# Event type → specialist agents (primary order)
ROUTING_TABLE: dict[str, list[str]] = {
    "credential_leak": [
        AgentName.DARK_WEB,
        AgentName.THREAT_INTEL,
        AgentName.INCIDENT_RESPONSE,
    ],
    "code_commit": [
        AgentName.SOURCE_CODE,
        AgentName.VULNERABILITY,
    ],
    "anomalous_login": [
        AgentName.INSIDER_THREAT,
        AgentName.SIEM_ANALYSIS,
    ],
    "ioc_observed": [
        AgentName.THREAT_INTEL,
        AgentName.FORENSICS,
        AgentName.GRAPH_QUERY,
    ],
    "cve_alert": [
        AgentName.VULNERABILITY,
        AgentName.COMPLIANCE,
        AgentName.NETWORK_SECURITY,
    ],
    "siem_alert": [
        AgentName.SIEM_ANALYSIS,
        AgentName.INCIDENT_RESPONSE,
    ],
    "network_anomaly": [
        AgentName.NETWORK_SECURITY,
        AgentName.GRAPH_QUERY,
    ],
    "compliance_gap": [
        AgentName.COMPLIANCE,
        AgentName.REPORTING,
    ],
    "unknown": [
        AgentName.THREAT_INTEL,
    ],
}

PRIORITY_BY_SEVERITY: dict[str, str] = {
    "critical": "P0",
    "high": "P1",
    "medium": "P2",
    "low": "P3",
    "info": "P3",
}


def select_agents_for_event(event: dict[str, Any]) -> list[str]:
    """Return ordered agent list for an inbound security event."""
    from packages.core.workflow_templates import agents_for_event

    event_type = str(event.get("type", "unknown"))
    fallback = list(ROUTING_TABLE.get(event_type, ROUTING_TABLE["unknown"]))
    return agents_for_event(event, fallback)


def resolve_priority(event: dict[str, Any]) -> str:
    """Derive P0–P3 priority from event fields or workflow template."""
    from packages.core.workflow_templates import priority_for_event

    if explicit := event.get("priority"):
        return str(explicit)
    severity = str(event.get("severity", "medium")).lower()
    fallback = PRIORITY_BY_SEVERITY.get(severity, "P2")
    return priority_for_event(event, fallback)


def should_run_parallel(priority: str) -> bool:
    """P0/P1 agents run in parallel; P2/P3 sequential."""
    return priority in ("P0", "P1")
