"""Week 2 routing tests."""

from agents.orchestrator.routing import resolve_priority, select_agents_for_event, should_run_parallel


def test_credential_leak_routes_dark_web_first() -> None:
    agents = select_agents_for_event({"type": "credential_leak"})
    assert agents[0] == "dark-web-agent"
    assert "threat-intel-agent" in agents


def test_code_commit_routes_source_code() -> None:
    agents = select_agents_for_event({"type": "code_commit"})
    assert agents[0] == "source-code-agent"


def test_critical_severity_maps_to_p0() -> None:
    assert resolve_priority({"severity": "critical"}) == "P0"


def test_p0_runs_parallel() -> None:
    assert should_run_parallel("P0") is True
    assert should_run_parallel("P2") is False
