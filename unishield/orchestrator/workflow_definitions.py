"""Fixed workflow definitions."""

WORKFLOW_DEFINITIONS: dict[str, dict] = {
    "full-security-audit": {
        "label": "Full Security Audit",
        "description": "Complete scan across all agents",
        "estimated_minutes": 45,
        "steps": [
            ["UniShield-Web"],
            ["UniShield-SCR", "UniShield-Insider"],
            ["UniShield-AF", "UniShield-ASM"],
            ["UniShield-CMA", "UniShield-CloudSec"],
            ["UniShield-Reporting"],
        ],
    },
    "incident-response": {
        "label": "Incident Response",
        "description": "Fast triage for active incident",
        "estimated_minutes": 12,
        "steps": [
            ["UniShield-Web"],
            ["UniShield-AF", "UniShield-Insider"],
            ["UniShield-Reporting"],
        ],
    },
    "code-review-only": {
        "label": "Code Review",
        "description": "Source code + supply chain scan",
        "estimated_minutes": 20,
        "steps": [
            ["UniShield-SCR"],
            ["UniShield-CMA"],
            ["UniShield-Reporting"],
        ],
    },
    "cloud-posture-check": {
        "label": "Cloud Posture Check",
        "description": "Cloud misconfiguration + attack surface",
        "estimated_minutes": 18,
        "steps": [
            ["UniShield-ASM", "UniShield-CloudSec"],
            ["UniShield-CMA"],
            ["UniShield-Reporting"],
        ],
    },
    "compliance-readiness": {
        "label": "Compliance Readiness",
        "description": "Framework gap analysis before audit",
        "estimated_minutes": 30,
        "steps": [
            ["UniShield-SCR", "UniShield-CloudSec"],
            ["UniShield-CMA"],
            ["UniShield-Reporting"],
        ],
    },
    "threat-hunt": {
        "label": "Threat Hunt",
        "description": "Dark web + behavioral + adversary simulation",
        "estimated_minutes": 15,
        "steps": [
            ["UniShield-Web"],
            ["UniShield-Insider", "UniShield-AF"],
            ["UniShield-Reporting"],
        ],
    },
}
