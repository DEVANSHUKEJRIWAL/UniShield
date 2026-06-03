"""Fixed workflow definitions — lowercase OpenClaw agent IDs."""

WORKFLOW_DEFINITIONS: dict[str, dict] = {
    "full-security-audit": {
        "label": "Full Security Audit",
        "description": "Complete scan across all agents",
        "estimated_minutes": 45,
        "steps": [
            ["unishield-web"],
            ["unishield-scr", "unishield-insider"],
            ["unishield-af", "unishield-asm"],
            ["unishield-cma", "unishield-cloudsec"],
            ["unishield-reporting"],
        ],
    },
    "incident-response": {
        "label": "Incident Response",
        "description": "Fast triage for active incident",
        "estimated_minutes": 12,
        "steps": [
            ["unishield-web"],
            ["unishield-af", "unishield-insider"],
            ["unishield-reporting"],
        ],
    },
    "code-review-only": {
        "label": "Code Review",
        "description": "Source code + supply chain scan",
        "estimated_minutes": 20,
        "steps": [
            ["unishield-scr"],
            ["unishield-cma"],
            ["unishield-reporting"],
        ],
    },
    "cloud-posture-check": {
        "label": "Cloud Posture Check",
        "description": "Cloud misconfiguration + attack surface",
        "estimated_minutes": 18,
        "steps": [
            ["unishield-asm", "unishield-cloudsec"],
            ["unishield-cma"],
            ["unishield-reporting"],
        ],
    },
    "compliance-readiness": {
        "label": "Compliance Readiness",
        "description": "Framework gap analysis before audit",
        "estimated_minutes": 30,
        "steps": [
            ["unishield-scr", "unishield-cloudsec"],
            ["unishield-cma"],
            ["unishield-reporting"],
        ],
    },
    "threat-hunt": {
        "label": "Threat Hunt",
        "description": "Dark web + behavioral + adversary simulation",
        "estimated_minutes": 15,
        "steps": [
            ["unishield-web"],
            ["unishield-insider", "unishield-af"],
            ["unishield-reporting"],
        ],
    },
}
