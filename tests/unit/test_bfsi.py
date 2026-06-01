"""Phase 2 BFSI schema tests."""

from packages.core.bfsi import (
    BFSIFinding,
    bfsi_to_agent_finding,
    confidence_label,
    regulators_for_industry,
    severity_from_risk_score,
    stable_bfsi_id,
)


def test_stable_bfsi_id_is_deterministic() -> None:
    a = stable_bfsi_id("dw", "meridian.com", "hibp")
    b = stable_bfsi_id("dw", "meridian.com", "hibp")
    assert a == b
    assert a.startswith("dw-")


def test_regulators_for_banking() -> None:
    regs = regulators_for_industry("banking")
    assert "RBI Cyber Resilience Framework" in regs


def test_severity_from_risk_score() -> None:
    assert severity_from_risk_score(85) == "critical"
    assert severity_from_risk_score(65) == "high"
    assert severity_from_risk_score(40) == "medium"
    assert severity_from_risk_score(10) == "low"


def test_confidence_label_buckets() -> None:
    assert confidence_label(0.9) == "high"
    assert confidence_label(0.7) == "medium"
    assert confidence_label(0.5) == "low"


def test_bfsi_to_agent_finding() -> None:
    bfsi = BFSIFinding(
        id="test-1",
        agentId="unishield-darkweb",
        kind="leaked-credential",
        severity="high",
        confidence="medium",
        title="Test",
        description="Desc",
    )
    finding = bfsi_to_agent_finding(bfsi, "meridian-financial", "dark-web-agent", finding_type="breach")
    assert finding.type == "breach"
    assert finding.raw["kind"] == "leaked-credential"
