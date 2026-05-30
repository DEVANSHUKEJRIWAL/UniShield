"""Orchestrator workflow templates (Week 5)."""

from typing import Any

from packages.shared_types.constants import AgentName

WORKFLOW_TEMPLATES: dict[str, dict[str, Any]] = {
    "credential_breach_response": {
        "event_types": ["credential_leak"],
        "priority": "P0",
        "agents": [AgentName.DARK_WEB, AgentName.THREAT_INTEL, AgentName.INCIDENT_RESPONSE],
        "description": "Credential exposure — parallel dark web, intel, and IR triage",
    },
    "code_supply_chain_review": {
        "event_types": ["code_commit"],
        "priority": "P1",
        "agents": [AgentName.SOURCE_CODE, AgentName.VULNERABILITY, AgentName.COMPLIANCE],
        "description": "SAST + CVE + compliance mapping for commits",
    },
    "insider_ueba_triage": {
        "event_types": ["anomalous_login", "insider_risk"],
        "priority": "P1",
        "agents": [AgentName.INSIDER_THREAT, AgentName.SIEM_ANALYSIS, AgentName.FORENSICS],
        "description": "UEBA anomaly with SIEM correlation and forensics",
    },
    "siem_incident_workflow": {
        "event_types": ["siem_alert", "log_anomaly"],
        "priority": "P1",
        "agents": [AgentName.SIEM_ANALYSIS, AgentName.INCIDENT_RESPONSE, AgentName.FORENSICS],
        "description": "SIEM alert triage and containment playbook",
    },
    "cve_remediation": {
        "event_types": ["cve_alert", "vulnerability"],
        "priority": "P1",
        "agents": [AgentName.VULNERABILITY, AgentName.NETWORK_SECURITY, AgentName.COMPLIANCE],
        "description": "CVE prioritisation with network exposure and compliance",
    },
    "compliance_reporting": {
        "event_types": ["compliance_gap"],
        "priority": "P3",
        "agents": [AgentName.COMPLIANCE, AgentName.REPORTING],
        "description": "Compliance gap analysis and executive reporting",
    },
}


def resolve_workflow_template(event: dict[str, Any]) -> dict[str, Any] | None:
    """Match event to a named workflow template."""
    explicit = event.get("workflow") or event.get("workflow_template")
    if explicit and explicit in WORKFLOW_TEMPLATES:
        return WORKFLOW_TEMPLATES[str(explicit)]
    event_type = str(event.get("type", ""))
    for template in WORKFLOW_TEMPLATES.values():
        if event_type in template.get("event_types", []):
            return template
    return None


def agents_for_event(event: dict[str, Any], fallback_agents: list[str]) -> list[str]:
    """Return agents from workflow template or routing fallback."""
    template = resolve_workflow_template(event)
    if template:
        return list(template["agents"])
    return fallback_agents


def priority_for_event(event: dict[str, Any], fallback_priority: str) -> str:
    """Return priority from workflow template or severity fallback."""
    template = resolve_workflow_template(event)
    if template and template.get("priority"):
        return str(template["priority"])
    return fallback_priority
