"""Tests for SCR stage progress tracking."""

from __future__ import annotations

import pytest
import pytest_asyncio
from fakeredis import aioredis as fakeredis

from backend.scr.scr_progress import ScrProgressTracker


@pytest_asyncio.fixture
async def tracker():
    redis = fakeredis.FakeRedis(decode_responses=True)
    return ScrProgressTracker(redis)


@pytest.mark.asyncio
async def test_scr_progress_stages(tracker: ScrProgressTracker):
    await tracker.start("WF-test")
    await tracker.set_stage("WF-test", "acquisition", "done", detail="10 files")
    await tracker.set_stage("WF-test", "detection", "running")

    progress = await tracker.get("WF-test")
    assert progress is not None
    assert progress["current_stage"] == "detection"
    stages = {s["id"]: s["status"] for s in progress["stages"]}
    assert stages["acquisition"] == "done"
    assert stages["detection"] == "running"


@pytest.mark.asyncio
async def test_scr_progress_complete(tracker: ScrProgressTracker):
    await tracker.start("WF-done")
    await tracker.complete("WF-done")
    progress = await tracker.get("WF-done")
    assert progress is not None
    assert all(s["status"] == "done" for s in progress["stages"])
    assert progress.get("completed_at")
