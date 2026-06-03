"""Dynamic routing rules — lowercase OpenClaw agent IDs."""

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
        "after": "web",
        "condition": lambda s, w: s.critical_count > 0,
        "next_agents": ["unishield-scr", "unishield-insider"],
        "priority": 1,
        "reason": "Credential leak found — scan code and flag insider anomalies",
    },
    {
        "after": "web",
        "condition": lambda s, w: s.critical_count == 0,
        "next_agents": ["unishield-asm"],
        "priority": 2,
        "reason": "No credentials leaked — check external attack surface only",
    },
    {
        "after": "scr",
        "condition": lambda s, w: _correlated(s),
        "next_agents": ["unishield-af"],
        "priority": 1,
        "reason": "Finding matches active incident TTP — prioritise AF",
    },
    {
        "after": "scr",
        "condition": lambda s, w: s.secret_findings_count > 0,
        "next_agents": ["unishield-cloudsec"],
        "priority": 2,
        "reason": "Secrets found in code — check cloud for live exposure",
        "also": True,
    },
    {
        "after": "scr",
        "condition": lambda s, w: s.risk_score >= 80,
        "next_agents": ["unishield-af", "unishield-cma"],
        "priority": 3,
        "reason": "Critical findings — correlate threat intel and map compliance gaps",
    },
    {
        "after": "scr",
        "condition": lambda s, w: 50 <= s.risk_score < 80,
        "next_agents": ["unishield-cma"],
        "priority": 4,
        "reason": "Medium risk — compliance mapping sufficient",
    },
    {
        "after": "scr",
        "condition": lambda s, w: s.risk_score < 50,
        "next_agents": ["unishield-reporting"],
        "priority": 5,
        "reason": "Low risk — go straight to report",
    },
    {
        "after": "af",
        "condition": lambda s, w: bool(s.kill_chain_stage and s.kill_chain_stage >= 3),
        "next_agents": ["unishield-reporting"],
        "priority": 1,
        "reason": "Stage 3+ kill chain — get exec brief out, pause for CISO",
        "pause": True,
    },
    {
        "after": "af",
        "condition": lambda s, w: not s.kill_chain_stage or s.kill_chain_stage < 3,
        "next_agents": ["unishield-cma", "unishield-reporting"],
        "priority": 2,
        "reason": "Threat identified but not critical — map controls and report",
    },
    {
        "after": "cma",
        "condition": lambda s, w: bool(s.audit_due_days and s.audit_due_days <= 30),
        "next_agents": ["unishield-reporting"],
        "priority": 1,
        "reason": "Audit imminent — expedite compliance report",
    },
    {
        "after": "cma",
        "condition": lambda s, w: True,
        "next_agents": ["unishield-reporting"],
        "priority": 2,
        "reason": "Analysis complete — generate report",
    },
    {
        "after": "reporting",
        "condition": lambda s, w: s.requires_human_approval,
        "next_agents": [],
        "priority": 1,
        "reason": "CRITICAL findings — pause for CISO approval",
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
