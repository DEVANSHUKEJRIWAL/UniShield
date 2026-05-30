"""Insider baseline persistence tests."""

import os

import pytest

os.environ.setdefault("UNISHIELD_USE_SQLITE", "1")

from packages.core.database import init_db
from packages.core.persistence import get_insider_baseline, upsert_insider_baseline


@pytest.fixture(autouse=True)
async def setup_db() -> None:
    await init_db()


@pytest.mark.asyncio
async def test_upsert_and_get_baseline() -> None:
    await upsert_insider_baseline(
        "meridian-financial",
        "alice",
        {"window30d": {"avg_logins": 20}},
        peer_group="finance",
    )
    row = await get_insider_baseline("meridian-financial", "alice")
    assert row is not None
    assert row["peer_group"] == "finance"
    assert row["window30d"]["avg_logins"] == 20
