"""Dynamic routing rules evaluated by the decision engine."""

from __future__ import annotations

from typing import Callable

from unishield.orchestrator.workflow_state import WorkflowState
from unishield.schemas.decision_surface import AgentDecisionSurface

RuleCondition = Callable[[AgentDecisionSurface, WorkflowState], bool]


def _get_extra(surface: AgentDecisionSurface, workflow: WorkflowState, key: str, default: int = 0) -> int:
    """Read extra routing fields stored in workflow context or surface."""
    ctx = workflow.context.get("agent_extras", {}).get(surface.agent_id, {})
    return int(ctx.get(key, default))


ROUTING_RULES: list[dict] = [
    # After UniShield-Web
    {
        "after": "UniShield-Web",
        "condition": lambda s, w: _get_extra(s, w, "credential_dumps") > 0,
        "next_agents": ["UniShield-SCR", "UniShield-Insider"],
        "priority": 1,
        "reason": "Credential dumps detected — trigger SCR and Insider",
    },
    {
        "after": "UniShield-Web",
        "condition": lambda s, w: _get_extra(s, w, "credential_dumps") == 0
        and _get_extra(s, w, "phishing_domains") > 0,
        "next_agents": ["UniShield-ASM"],
        "priority": 2,
        "reason": "Phishing domains detected — trigger ASM",
    },
    {
        "after": "UniShield-Web",
        "condition": lambda s, w: bool(w.context.get("threat_actor_identified")),
        "next_agents": ["UniShield-AF"],
        "priority": 0,
        "reason": "Threat actor identified — trigger AF with HIGH priority",
    },
    # After UniShield-SCR
    {
        "after": "UniShield-SCR",
        "condition": lambda s, w: s.risk_score >= 80,
        "next_agents": ["UniShield-AF", "UniShield-CMA"],
        "priority": 4,
        "reason": "High risk score — trigger AF and CMA in parallel",
    },
    {
        "after": "UniShield-SCR",
        "condition": lambda s, w: 50 <= s.risk_score < 80,
        "next_agents": ["UniShield-CMA"],
        "priority": 5,
        "reason": "Medium risk score — trigger CMA only",
    },
    {
        "after": "UniShield-SCR",
        "condition": lambda s, w: s.risk_score < 50,
        "next_agents": ["UniShield-Reporting"],
        "priority": 6,
        "reason": "Low risk score — trigger Reporting directly",
    },
    {
        "after": "UniShield-SCR",
        "condition": lambda s, w: s.secret_findings_count > 0,
        "next_agents": ["UniShield-CloudSec"],
        "priority": 7,
        "reason": "Secret findings detected — also trigger CloudSec",
        "also": True,
    },
    {
        "after": "UniShield-SCR",
        "condition": lambda s, w: s.correlated_to_incident,
        "next_agents": ["UniShield-AF"],
        "priority": 0,
        "reason": "Correlated to incident — trigger AF with CRITICAL priority",
    },
    # After UniShield-AF
    {
        "after": "UniShield-AF",
        "condition": lambda s, w: (s.kill_chain_stage or 0) >= 3,
        "next_agents": ["UniShield-Reporting"],
        "priority": 9,
        "reason": "Kill chain stage >= 3 — trigger Reporting and pause",
        "pause": True,
    },
    {
        "after": "UniShield-AF",
        "condition": lambda s, w: (s.kill_chain_stage or 0) < 3
        and float(w.context.get("confidence", 0)) >= 0.7,
        "next_agents": ["UniShield-CMA", "UniShield-Reporting"],
        "priority": 10,
        "reason": "High confidence — trigger CMA and Reporting",
    },
    # After UniShield-CMA
    {
        "after": "UniShield-CMA",
        "condition": lambda s, w: _get_extra(s, w, "critical_gaps") > 0
        and (s.audit_due_days or 999) <= 30,
        "next_agents": ["UniShield-Reporting"],
        "priority": 11,
        "reason": "Critical gaps with audit due — trigger Reporting HIGH",
    },
    {
        "after": "UniShield-CMA",
        "condition": lambda s, w: True,
        "next_agents": ["UniShield-Reporting"],
        "priority": 12,
        "reason": "All prereqs done — trigger Reporting",
    },
    # After UniShield-Reporting
    {
        "after": "UniShield-Reporting",
        "condition": lambda s, w: s.requires_human_approval,
        "next_agents": [],
        "priority": 13,
        "reason": "Requires human approval — pause workflow, notify CISO",
        "pause": True,
    },
    {
        "after": "UniShield-Reporting",
        "condition": lambda s, w: not s.requires_human_approval,
        "next_agents": [],
        "priority": 14,
        "reason": "No human approval needed — complete workflow",
        "complete": True,
    },
]
