"""Unit tests for normalised event schema."""

from datetime import UTC, datetime

from packages.event_schema.models import NormalisedEvent


def test_normalised_event_validates() -> None:
    """NormalisedEvent accepts valid payload."""
    event = NormalisedEvent(
        event_id="550e8400-e29b-41d4-a716-446655440000",
        tenant_id="meridian-financial",
        source_type="siem",
        source_vendor="splunk",
        timestamp=datetime.now(UTC),
        severity="high",
        category="auth",
        entity_type="user",
        entity_id="user-001",
        raw={"event": "failed_login"},
        mitre_ttps=["T1078"],
        cvss_tags=[],
    )
    assert event.schema_version == "1.0"
    assert event.severity == "high"
