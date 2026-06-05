"""Tests for ActionGate Postgres timestamp handling."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from backend.infrastructure.postgres_client import to_pg_timestamp
from backend.orchestrator.action_gate import ActionGate
from backend.schemas.action_contract import ActionScope, ProposedAction


def test_to_pg_timestamp_strips_timezone():
    aware = datetime(2026, 6, 5, 10, 10, 58, tzinfo=UTC)
    naive = to_pg_timestamp(aware)
    assert naive is not None
    assert naive.tzinfo is None
    assert naive.hour == 10


@pytest.mark.asyncio
async def test_action_gate_propose_uses_naive_timestamp():
    postgres = AsyncMock()
    postgres.execute = AsyncMock(return_value="INSERT 1")
    kafka = AsyncMock()
    kafka.publish = AsyncMock()
    state_store = AsyncMock()
    gate = ActionGate(postgres, kafka, state_store)

    action = ProposedAction(
        action_id="HITL-test",
        workflow_id="WF-test",
        agent_id="unishield-scr",
        action_type="remediation_review",
        scope=ActionScope.WRITE_SCOPE,
        target="app.py",
        description="{}",
        impact="review",
        reversible=True,
        proposed_at=datetime.now(UTC),
    )
    await gate.propose(action)

    proposed_at_arg = postgres.execute.call_args.args[11]
    assert proposed_at_arg.tzinfo is None
