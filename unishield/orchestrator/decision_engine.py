"""Dynamic routing decision engine."""

from __future__ import annotations

import logging

from unishield.orchestrator.routing_rules import ROUTING_RULES
from unishield.orchestrator.workflow_state import WorkflowState
from unishield.schemas.decision_surface import AgentDecisionSurface

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Evaluates routing rules against agent decision surfaces."""

    def evaluate(
        self,
        workflow: WorkflowState,
        completed_agent: str,
        surface: AgentDecisionSurface,
    ) -> list[str]:
        """Return list of agent IDs to trigger next. Empty list means workflow is done."""
        applicable = [
            r
            for r in ROUTING_RULES
            if r["after"] == completed_agent
        ]
        applicable.sort(key=lambda r: r["priority"])

        next_agents: list[str] = []
        matched_primary = False

        for rule in applicable:
            try:
                if not rule["condition"](surface, workflow):
                    continue
            except Exception:
                logger.exception("Rule condition failed: %s", rule.get("reason"))
                continue

            if rule.get("complete"):
                return []

            if rule.get("pause"):
                workflow.context["pending_pause"] = rule["reason"]
                return rule.get("next_agents", [])

            if rule.get("also"):
                for agent in rule["next_agents"]:
                    if agent not in next_agents:
                        next_agents.append(agent)
                continue

            if not matched_primary:
                next_agents = list(rule["next_agents"])
                matched_primary = True

        return next_agents

    def should_escalate(
        self,
        completed_agent: str,
        surface: AgentDecisionSurface,
        workflow: WorkflowState,
    ) -> bool:
        """Return True if fixed plan should be abandoned for dynamic routing."""
        if surface.correlated_to_incident:
            return True
        if surface.risk_score >= 80 and workflow.flow_type == "fixed":
            return True
        if (surface.kill_chain_stage or 0) >= 3:
            return True
        active_ttps = workflow.context.get("threat_actor_ttps", [])
        matched_ttps = workflow.context.get("matched_ttps", [])
        if active_ttps and matched_ttps:
            return True
        return False
