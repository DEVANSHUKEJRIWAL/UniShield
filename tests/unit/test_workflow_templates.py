"""Workflow template tests."""

from packages.core.workflow_templates import resolve_workflow_template, agents_for_event, priority_for_event
from agents.orchestrator.routing import select_agents_for_event, resolve_priority
from packages.shared_types.constants import AgentName


def test_credential_leak_workflow() -> None:
    event = {"type": "credential_leak", "severity": "critical"}
    template = resolve_workflow_template(event)
    assert template is not None
    agents = select_agents_for_event(event)
    assert AgentName.DARK_WEB in agents
    assert resolve_priority(event) == "P0"


def test_compliance_workflow_priority() -> None:
    event = {"type": "compliance_gap", "severity": "low"}
    assert priority_for_event(event, "P3") == "P3"
    agents = agents_for_event(event, [])
    assert AgentName.REPORTING in agents
