"""Dynamic routing rules — SCR workflow pipeline."""

from __future__ import annotations

from unishield.orchestrator.workflow_state import WorkflowState
from unishield.schemas.decision_surface import AgentDecisionSurface


def _correlated(surface: AgentDecisionSurface) -> bool:
    if surface.correlated_to_incident:
        return True
    if isinstance(surface.correlated_to_incident, str):
        return surface.correlated_to_incident.lower() in ("true", "1", "yes")
    return False


ROUTING_RULES: list[dict] = [
    {
        "after": "scr",
        "condition": lambda s, w: _correlated(s) or s.risk_score >= 80 or s.secret_findings_count > 0,
        "next_agents": ["unishield-cma"],
        "priority": 1,
        "reason": "High-risk or incident-correlated findings — map compliance gaps",
    },
    {
        "after": "scr",
        "condition": lambda s, w: 50 <= s.risk_score < 80,
        "next_agents": ["unishield-cma"],
        "priority": 2,
        "reason": "Medium risk — compliance mapping",
    },
    {
        "after": "scr",
        "condition": lambda s, w: s.risk_score < 50,
        "next_agents": ["unishield-reporting"],
        "priority": 3,
        "reason": "Low risk — go straight to report",
    },
    {
        "after": "cma",
        "condition": lambda s, w: True,
        "next_agents": ["unishield-reporting"],
        "priority": 1,
        "reason": "Compliance mapping complete — generate report",
    },
    {
        "after": "reporting",
        "condition": lambda s, w: s.requires_human_approval,
        "next_agents": [],
        "priority": 1,
        "reason": "CRITICAL findings — pause for human approval",
        "pause": True,
    },
    {
        "after": "reporting",
        "condition": lambda s, w: not s.requires_human_approval,
        "next_agents": [],
        "priority": 2,
        "reason": "Workflow complete",
        "complete": True,
    },
]
