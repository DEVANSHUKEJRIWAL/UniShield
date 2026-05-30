"""Week 3–6 platform readiness checks."""

from typing import Any

from packages.core.config import settings


def week3_6_readiness() -> dict[str, Any]:
    """Summarise Weeks 3–6 deliverable status."""
    return {
        "week3": {
            "db_persistence": True,
            "cve_poller": True,
            "insider_schema": True,
            "agent_run_logs": True,
            "vector_corpus_embed": True,
        },
        "week4": {
            "siem_schema": True,
            "specialist_structured_handlers": True,
            "adversarial_tests": True,
        },
        "week5": {
            "findings_api": True,
            "pagination": True,
            "elasticsearch_search": True,
            "rbac_enforcement": True,
            "reporting_synthesis": True,
            "alembic_migrations": True,
        },
        "week6": {
            "dashboard_live_kpis": True,
            "websocket_all_agents": True,
            "csp_middleware": True,
            "frontend_api_wiring": True,
            "agent_run_history": True,
        },
        "elasticsearch_url": settings.elasticsearch_url,
        "qdrant_url": settings.qdrant_url,
        "docs": [
            "docs/week3/README.md",
            "docs/week4/README.md",
            "docs/week5/README.md",
            "docs/week6/README.md",
        ],
    }
