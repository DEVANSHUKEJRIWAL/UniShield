"""Tests for live workflow runners (CMA, reporting)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from fakeredis import aioredis as fakeredis

from backend.cma.cma_runner import CMARunner
from backend.reporting.reporting_runner import ReportingRunner
from backend.memory.shared_memory import SharedMemoryClient


@pytest_asyncio.fixture
async def shared():
    redis = fakeredis.FakeRedis(decode_responses=True)
    client = SharedMemoryClient(redis)
    yield client
    await redis.aclose()


@pytest.mark.asyncio
async def test_cma_inherits_scr_risk(shared):
    await shared.write_agent_output(
        "WF-live",
        "scr",
        {
            "agent_id": "scr",
            "risk_score": 100,
            "highest_severity": "CRITICAL",
            "critical_count": 2,
            "secret_findings_count": 3,
            "top_findings": [
                {"category": "code_execution", "severity": "HIGH", "file_path": "eval.php"}
            ],
        },
    )
    runner = CMARunner(shared)
    await runner.run("WF-live", "client-1")
    cma = await shared.read_agent_output("WF-live", "cma")
    assert cma["risk_score"] == 100
    assert cma["highest_severity"] == "CRITICAL"
    assert cma["gaps_identified"] >= 1


@pytest.mark.asyncio
async def test_reporting_inherits_scr_risk(shared):
    await shared.write_agent_output(
        "WF-live2",
        "scr",
        {
            "agent_id": "scr",
            "risk_score": 100,
            "highest_severity": "CRITICAL",
            "critical_count": 0,
            "secret_findings_count": 3,
            "files_discovered": 113,
            "top_findings": [],
        },
    )
    await shared.write_agent_output(
        "WF-live2",
        "cma",
        {
            "agent_id": "cma",
            "risk_score": 100,
            "highest_severity": "CRITICAL",
            "critical_count": 0,
            "gaps_identified": 4,
        },
    )
    runner = ReportingRunner(shared)
    await runner.run("WF-live2", "client-1")
    reporting = await shared.read_agent_output("WF-live2", "reporting")
    assert reporting["risk_score"] == 100
    assert reporting["highest_severity"] == "CRITICAL"
    assert reporting["requires_human_approval"] is True
