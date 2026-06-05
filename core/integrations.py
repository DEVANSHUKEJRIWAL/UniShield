"""Integration readiness for orchestrator + SCR stack."""

import os
from typing import Any

from core.api_keys import anthropic_key_format_valid, anthropic_live_enabled
from core.config import settings


def integration_status() -> dict[str, Any]:
    """Return which services are configured for workflow scans."""
    return {
        "anthropic": {
            "configured": bool(settings.anthropic_api_key),
            "key_format_valid": anthropic_key_format_valid(settings.anthropic_api_key),
            "live_enabled": anthropic_live_enabled(),
            "required_for": "SCR Stage 7 AI enrichment (optional without key)",
            "env": "ANTHROPIC_API_KEY",
        },
        "orchestrator": {
            "configured": bool(os.getenv("UNISHIELD_ORCHESTRATOR_URL", "http://127.0.0.1:8001")),
            "required_for": "Security workflows and connected repo scans",
            "env": "UNISHIELD_ORCHESTRATOR_URL",
        },
        "redis": {
            "configured": bool(settings.redis_url),
            "required_for": "Orchestrator shared memory and workflow state",
            "env": "REDIS_URL",
        },
        "postgresql": {
            "configured": not settings.uses_sqlite,
            "required_for": "Repo connections and workflow persistence (SQLite OK for local dev)",
            "env": "UNISHIELD_USE_POSTGRES + POSTGRES_URI",
        },
    }


def stack_readiness() -> dict[str, Any]:
    """Summarise orchestrator + SCR readiness."""
    integrations = integration_status()
    return {
        "orchestrator_url_set": integrations["orchestrator"]["configured"],
        "redis_configured": integrations["redis"]["configured"],
        "database_postgres": integrations["postgresql"]["configured"],
        "scr_ai_enrichment": anthropic_live_enabled(),
        "docs": "docs/STRUCTURE.md",
    }
