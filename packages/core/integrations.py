"""External integration and API-key readiness checks (Week 1)."""

from typing import Any

from packages.core.api_keys import anthropic_key_format_valid, anthropic_live_enabled
from packages.core.config import settings


def integration_status() -> dict[str, Any]:
    """Return which Week 1 data sources and services are configured."""
    return {
        "anthropic": {
            "configured": bool(settings.anthropic_api_key),
            "key_format_valid": anthropic_key_format_valid(settings.anthropic_api_key),
            "live_enabled": anthropic_live_enabled(),
            "required_for": "Live agent reasoning (without valid key: mock findings)",
            "env": "ANTHROPIC_API_KEY",
        },
        "virustotal": {
            "configured": bool(settings.virustotal_api_key),
            "required_for": "Threat Intel Agent — indicator reputation",
            "env": "VIRUSTOTAL_API_KEY",
        },
        "shodan": {
            "configured": bool(settings.shodan_api_key),
            "required_for": "Threat Intel / Network agents — IP intelligence",
            "env": "SHODAN_API_KEY",
        },
        "nvd": {
            "configured": bool(settings.nvd_api_key),
            "required_for": "Vulnerability Agent — CVE lookups (optional key, rate limits apply)",
            "env": "NVD_API_KEY",
        },
        "mitre_attack": {
            "configured": True,
            "required_for": "MITRE ATT&CK — STIX/TAXII + local corpus (no API key required)",
            "env": None,
        },
        "osint_feeds": {
            "configured": bool(settings.osint_feed_urls),
            "required_for": "Dark Web / OSINT agents — configurable feed URLs",
            "env": "OSINT_FEED_URLS",
        },
        "hibp": {
            "configured": bool(settings.hibp_api_key),
            "required_for": "Dark Web Agent — domain breach lookups",
            "env": "HIBP_API_KEY",
        },
        "okta": {
            "configured": bool(settings.okta_domain and settings.okta_api_token),
            "required_for": "Insider Threat Agent — Okta access logs",
            "env": "OKTA_DOMAIN + OKTA_API_TOKEN",
        },
        "hr_feed": {
            "configured": bool(settings.hr_feed_url),
            "required_for": "Insider Threat Agent — HR offboarding/risk flags",
            "env": "HR_FEED_URL",
        },
        "redis": {
            "configured": bool(settings.redis_url),
            "required_for": "Agent message bus, HITL queue, WebSocket backplane",
            "env": "REDIS_URL",
        },
        "postgresql": {
            "configured": not settings.uses_sqlite,
            "required_for": "Week 1 canonical stack (SQLite OK for quick local dev)",
            "env": "UNISHIELD_USE_POSTGRES + POSTGRES_URI",
        },
    }


def week1_readiness() -> dict[str, Any]:
    """Summarise Week 1 integration checklist."""
    integrations = integration_status()
    optional_live_keys = ["virustotal", "shodan", "nvd", "osint_feeds"]
    configured_optional = sum(
        1 for k in optional_live_keys if integrations[k]["configured"]
    )
    return {
        "week1_stack_postgres": integrations["postgresql"]["configured"],
        "week1_stack_redis_url_set": integrations["redis"]["configured"],
        "live_agent_reasoning": anthropic_live_enabled(),
        "external_intel_keys_configured": configured_optional,
        "external_intel_keys_total": len(optional_live_keys),
        "mitre_attack_ready": integrations["mitre_attack"]["configured"],
        "docs": "docs/week1/README.md",
    }
