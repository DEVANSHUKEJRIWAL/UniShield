"""Unit tests for risk scoring engine."""

from datetime import UTC, datetime

from services.risk_engine.models import RiskScore


def test_risk_score_composite_computation() -> None:
    """Composite score is computed from weighted dimensions."""
    score = RiskScore(
        finding_id="f-001",
        client_id="meridian-financial",
        timestamp=datetime.now(UTC),
        exploitability=0.8,
        cvss_base=0.7,
        business_criticality=0.9,
        regulatory_obligation=0.6,
        blast_radius=0.5,
        data_sensitivity=0.7,
        time_to_exploit=0.8,
        detection_confidence=0.85,
        remediation_complexity=0.4,
        compensating_controls=0.3,
        active_exploitation=0.6,
        compliance_deadline=0.5,
    )
    weights = {k: 1.0 for k in [
        "exploitability", "cvss_base", "business_criticality",
        "regulatory_obligation", "blast_radius", "data_sensitivity",
        "time_to_exploit", "detection_confidence", "remediation_complexity",
        "compensating_controls", "active_exploitation", "compliance_deadline",
    ]}
    composite = score.compute_composite(weights)
    assert 0.0 <= composite <= 1.0
    assert score.business_risk_label in ("Critical", "High", "Medium", "Low")
