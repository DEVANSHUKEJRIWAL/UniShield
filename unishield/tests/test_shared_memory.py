"""Tests for shared memory client."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from fakeredis import aioredis as fakeredis

from unishield.memory.shared_memory import AgentOutputNotReady, SharedMemoryClient


@pytest_asyncio.fixture
async def redis_client():
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def shared(redis_client):
    return SharedMemoryClient(redis_client)


@pytest.mark.asyncio
async def test_write_and_read_agent_output(shared):
    await shared.write_agent_output(
        "wf-1",
        "UniShield-SCR",
        {"risk_score": 75, "forward_to": ["UniShield-CMA"]},
    )
    data = await shared.read_agent_output("wf-1", "UniShield-SCR")
    assert data["risk_score"] == 75
    assert data["forward_to"] == ["UniShield-CMA"]


@pytest.mark.asyncio
async def test_read_decision_surface(shared):
    await shared.write_agent_output(
        "wf-1",
        "UniShield-SCR",
        {
            "agent_id": "UniShield-SCR",
            "completed_at": datetime.now(UTC).isoformat(),
            "risk_score": 87,
            "highest_severity": "HIGH",
            "requires_human_approval": False,
            "auto_remediation_safe": False,
            "forward_to": [],
            "critical_count": 2,
            "secret_findings_count": 1,
            "correlated_to_incident": True,
        },
    )
    surface = await shared.read_decision_surface("wf-1", "UniShield-SCR")
    assert surface.risk_score == 87
    assert surface.secret_findings_count == 1
    assert surface.correlated_to_incident is True


@pytest.mark.asyncio
async def test_agent_output_not_ready(shared):
    with pytest.raises(AgentOutputNotReady):
        await shared.read_agent_output("wf-missing", "UniShield-SCR")


@pytest.mark.asyncio
async def test_get_full_snapshot_and_clear(shared):
    await shared.write_agent_output("wf-2", "UniShield-SCR", {"risk_score": 50})
    await shared.write_agent_output("wf-2", "UniShield-Web", {"domains": 3})

    snapshot = await shared.get_full_snapshot("wf-2")
    assert "UniShield-SCR" in snapshot
    assert "UniShield-Web" in snapshot
    assert await shared.workflow_exists("wf-2")

    await shared.clear_workflow("wf-2")
    assert not await shared.workflow_exists("wf-2")


@pytest.mark.asyncio
async def test_read_multiple_agents(shared):
    await shared.write_agent_output("wf-3", "UniShield-SCR", {"risk_score": 60})
    await shared.write_agent_output("wf-3", "UniShield-Web", {"domains": 5})

    results = await shared.read_multiple_agents(
        "wf-3", ["UniShield-SCR", "UniShield-Web", "UniShield-Missing"]
    )
    assert "UniShield-SCR" in results
    assert "UniShield-Web" in results
    assert "UniShield-Missing" not in results
