"""Tests for post-HITL action execution."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.orchestrator.action_executor import ActionExecutor
from backend.orchestrator.action_gate import ActionGate
from backend.schemas.action_contract import ActionScope, ActionStatus, ProposedAction


class InMemoryKafka:
    async def publish(self, topic, payload, key=None):
        pass


class MockPostgres:
    def __init__(self):
        self.rows: dict[str, dict] = {}

    async def fetchrow(self, query, *args):
        return self.rows.get(args[0])

    async def execute(self, query, *args):
        if "UPDATE proposed_actions SET status=$1, executed_at" in query:
            action_id = args[2]
            if action_id in self.rows:
                self.rows[action_id]["status"] = args[0]
        elif "UPDATE proposed_actions" in query and "approved" in query:
            action_id = args[3]
            if action_id in self.rows:
                self.rows[action_id]["status"] = ActionStatus.APPROVED.value
        return "OK"


class MockStateStore:
    pass


@pytest.mark.asyncio
async def test_execute_approved_remediation():
    postgres = MockPostgres()
    kafka = InMemoryKafka()
    gate = ActionGate(postgres, kafka, MockStateStore())
    executor = ActionExecutor(postgres, gate, kafka)

    action_id = "HITL-WF-abc-f1"
    postgres.rows[action_id] = {
        "action_id": action_id,
        "workflow_id": "WF-abc",
        "action_type": "remediation_review",
        "status": ActionStatus.APPROVED.value,
        "target": "src/app.py",
        "description": '{"finding_id": "f1", "file_path": "src/app.py"}',
    }

    result = await executor.execute_approved(action_id, executed_by="analyst@meridian.com")
    assert result["status"] == "executed"
    assert postgres.rows[action_id]["status"] == ActionStatus.EXECUTED.value
