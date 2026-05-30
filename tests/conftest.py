"""Shared pytest fixtures and test database bootstrap."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

# Configure test environment before application imports in test modules.
os.environ.setdefault("UNISHIELD_USE_SQLITE", "1")
os.environ.setdefault("AUTO_SEED", "true")
os.environ.setdefault("ENABLE_CONNECTOR_INGEST", "0")
os.environ.setdefault("ENABLE_CVE_POLLER", "0")

_TEST_DB = Path(__file__).resolve().parents[1] / "data" / "unishield.db"


def _bootstrap_test_database() -> None:
    """Create schema and seed demo users before integration tests query the DB."""
    _TEST_DB.parent.mkdir(parents=True, exist_ok=True)
    from packages.core.database import bootstrap_dev_data

    asyncio.run(bootstrap_dev_data())


# Run when pytest loads conftest — before integration test modules import the app.
_bootstrap_test_database()


@pytest.fixture(scope="session", autouse=True)
def init_test_db() -> None:
    """Ensure DB schema + seed data exist for the full test session."""
    _bootstrap_test_database()
