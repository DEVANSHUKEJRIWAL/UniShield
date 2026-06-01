"""Week 1 integration status tests."""

from packages.core.integrations import integration_status, week1_readiness


def test_integration_status_includes_week1_sources() -> None:
    """Integration status covers Week 1 data sources."""
    status = integration_status()
    assert "virustotal" in status
    assert "shodan" in status
    assert "nvd" in status
    assert "mitre_attack" in status
    assert "osint_feeds" in status
    assert "hibp" in status
    assert status["mitre_attack"]["configured"] is True


def test_week1_readiness_summary() -> None:
    """Week 1 readiness returns summary block."""
    readiness = week1_readiness()
    assert "week1_stack_postgres" in readiness
    assert "external_intel_keys_configured" in readiness
    assert readiness["docs"] == "docs/week1/README.md"
