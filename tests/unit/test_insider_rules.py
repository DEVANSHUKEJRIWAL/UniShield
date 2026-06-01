"""Phase 2 insider rule engine tests."""

from packages.core.insider_rules import evaluate_insider_risk


def test_after_hours_rule_triggers() -> None:
    result = evaluate_insider_risk(
        "alice",
        [{"type": "login", "timestamp": "2024-11-01T23:30:00+00:00"}],
        {"window30d": {"avg_logins": 12}},
    )
    assert "after-hours" in result["triggeredRules"]
    assert result["riskScore"] >= 15


def test_privilege_escalation_high_score() -> None:
    result = evaluate_insider_risk(
        "bob",
        [{"type": "privilege_change", "timestamp": "2024-11-01T14:00:00+00:00"}],
    )
    assert "privilege-escalation" in result["triggeredRules"]
    assert result["riskScore"] >= 25
    assert result["severity"] in ("critical", "high", "medium", "low")


def test_foreign_ip_rule() -> None:
    result = evaluate_insider_risk(
        "carol",
        [{"type": "login", "country": "RU", "timestamp": "2024-11-01T10:00:00+00:00"}],
        {"home_country": "IN"},
    )
    assert "foreign-ip" in result["triggeredRules"]


def test_hr_flag_boosts_score() -> None:
    result = evaluate_insider_risk(
        "dave",
        [],
        {},
        hr_flags=[{"hr_flag": True, "offboarded": True}],
    )
    assert "hr-flag" in result["triggeredRules"]
    assert "post-offboarding" in result["triggeredRules"]
    assert result["riskScore"] >= 50
