"""Risk engine and HITL tests."""

from services.hitl_service.models import should_require_hitl
from services.risk_engine.service import risk_engine


def test_hitl_critical_always_required() -> None:
    """Critical severity always requires HITL."""
    assert should_require_hitl(0.99, "LOW", "CRITICAL")


def test_hitl_low_confidence_always_required() -> None:
    """Low confidence always requires HITL."""
    assert should_require_hitl(0.5, "LOW", "MEDIUM")


def test_risk_engine_scores_finding() -> None:
    """Risk engine produces composite score."""
    score = risk_engine.score_finding({"severity": "critical", "confidence": 0.9, "tenant_id": "test"})
    assert score.composite_score > 0
    assert score.business_risk_label in ("Critical", "High", "Medium", "Low")
