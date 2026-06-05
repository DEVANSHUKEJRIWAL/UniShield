"""Fixed workflow definitions — orchestrator + SCR focus."""

WORKFLOW_DEFINITIONS: dict[str, dict] = {
    "code-review-only": {
        "label": "Code Review",
        "description": "Source code review, compliance mapping, and executive report",
        "estimated_minutes": 20,
        "steps": [
            ["unishield-scr"],
            ["unishield-cma"],
            ["unishield-reporting"],
        ],
    },
    "compliance-readiness": {
        "label": "Compliance Readiness",
        "description": "SCR findings mapped to control frameworks before audit",
        "estimated_minutes": 30,
        "steps": [
            ["unishield-scr"],
            ["unishield-cma"],
            ["unishield-reporting"],
        ],
    },
    "incremental-pr-scan": {
        "label": "Incremental PR Scan",
        "description": "Diff-scoped source review for pull requests",
        "estimated_minutes": 10,
        "steps": [
            ["unishield-scr"],
            ["unishield-reporting"],
        ],
    },
}
