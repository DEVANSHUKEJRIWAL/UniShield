"""Unit tests for orchestrator dashboard metrics helpers."""

from services.api_gateway.routers.workflows import (
    _build_dashboard_widgets,
    _build_trend_and_sparklines,
    _build_workflow_agents,
    _normalize_agent_key,
    _pad_series,
    _risk_label_from_score,
)


def test_normalize_agent_key():
    assert _normalize_agent_key("unishield-scr") == "scr"
    assert _normalize_agent_key("scr") == "scr"


def test_risk_label_from_score():
    assert _risk_label_from_score(80) == "Elevated"
    assert _risk_label_from_score(55) == "Moderate"
    assert _risk_label_from_score(20) == "Low"


def test_pad_series():
    assert _pad_series([10, 20, 30]) == [10, 10, 10, 10, 20, 30]
    assert _pad_series([]) == [0, 0, 0, 0, 0, 0]


def test_build_trend_and_sparklines():
    points = [
        {"risk_score": 40, "critical_findings": 1, "total_findings": 3},
        {"risk_score": 55, "critical_findings": 2, "total_findings": 5},
    ]
    trend, spark = _build_trend_and_sparklines(points)
    assert len(trend) == 6
    assert trend[-1]["score"] == 55
    assert spark["findings"][-1] == 5


def test_build_workflow_agents_from_running():
    workflows = [
        {
            "status": "RUNNING",
            "agent_states": {"scr": "RUNNING", "cma": "PENDING", "reporting": "PENDING"},
        }
    ]
    agents = _build_workflow_agents(workflows)
    assert agents[0]["name"] == "cma"
    assert next(a for a in agents if a["name"] == "scr")["status"] == "running"


def test_build_workflow_agents_idle_defaults():
    agents = _build_workflow_agents([])
    assert len(agents) == 3
    assert all(a["status"] == "idle" for a in agents)


def test_build_dashboard_widgets_handles_stringified_scr_fields():
    snapshots = [
        {
            "risk_score": 40,
            "compliance_gaps": "[]",
            "sbom_summary": "{}",
            "top_findings": [],
        }
    ]
    widgets = _build_dashboard_widgets(
        snapshots,
        [],
        paused_workflows=0,
        running_workflows=0,
        completed_workflows=1,
    )
    assert widgets["vendor_risks"] == []
    assert widgets["compliance_pct"] == 100


def test_build_dashboard_widgets_from_scr():
    snapshots = [
        {
            "risk_score": 72,
            "compliance_gaps": ["PCI-6.5", "SOC2-CC6"],
            "sbom_summary": {"components": 12, "vulnerable": 2, "ecosystem": "npm"},
            "top_findings": [
                {"severity": "critical", "category": "secrets", "title": "API key in repo"},
                {"severity": "high", "category": "injection", "title": "SQLi vector"},
            ],
        }
    ]
    priority = [
        {"id": "1", "severity": "critical", "title": "API key in repo", "source": "unishield-scr", "time": "2026-01-01"},
        {"id": "2", "severity": "high", "title": "SQLi vector", "source": "unishield-scr", "time": "2026-01-01"},
    ]
    widgets = _build_dashboard_widgets(
        snapshots,
        priority,
        paused_workflows=1,
        running_workflows=1,
        completed_workflows=2,
    )
    assert widgets["vendor_risks"]
    assert widgets["threat_origins"]
    assert widgets["ai_brief"]["headline"] == "API key in repo"
    assert widgets["compliance_pct"] is not None
    assert widgets["severity_mix"]["critical"] > 0

