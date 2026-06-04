"""End-to-end workflow tests for repo-connected code review scans."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
import pytest_asyncio
from fakeredis import aioredis as fakeredis
from openclaw_sdk.core.config import ClientConfig

from unishield.agents.scr.tools.repo_acquirer import AcquisitionResult
from unishield.agents.scr.scr_runner import SCRRunner
from unishield.infrastructure.model_router import ModelRouter
from unishield.config.settings import settings
from unishield.memory.personal_memory import PersonalMemoryClient
from unishield.memory.shared_memory import SharedMemoryClient
from unishield.orchestrator.decision_engine import DecisionEngine
from unishield.orchestrator.finalizer import WorkflowFinalizer
from unishield.orchestrator.orchestrator import Orchestrator
from unishield.orchestrator.trigger_handler import TriggerHandler
from unishield.orchestrator.workflow_state import WorkflowStateStore


class InMemoryKafka:
    async def publish(self, topic: str, payload: dict, key: str | None = None) -> None:
        pass


class MockPostgres:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    async def execute(self, query: str, *args) -> str:
        import json

        workflow_id, client_id, snapshot, checksum, completed_at = args
        parsed = json.loads(snapshot) if isinstance(snapshot, str) else snapshot
        self.rows[workflow_id] = {"checksum": checksum, "snapshot": parsed}
        return "INSERT 1"

    async def fetchrow(self, query: str, *args) -> dict | None:
        return self.rows.get(args[0])


@pytest_asyncio.fixture
async def repo_scan_setup():
    redis = fakeredis.FakeRedis(decode_responses=True)
    shared = SharedMemoryClient(redis)
    personal = PersonalMemoryClient(redis)
    state_store = WorkflowStateStore(redis)
    kafka = InMemoryKafka()
    postgres = MockPostgres()
    finalizer = WorkflowFinalizer(shared, postgres, kafka, state_store)
    config = ClientConfig(mock_mode=True)
    scr_runner = SCRRunner(
        config, shared, personal, kafka, settings, ModelRouter(settings)
    )
    orch = Orchestrator(
        config,
        shared,
        state_store,
        DecisionEngine(),
        finalizer,
        kafka,
        settings,
        scr_runner,
    )
    handler = TriggerHandler(orch)
    return handler, scr_runner, postgres, state_store


@pytest.mark.asyncio
async def test_repo_scan_code_review_includes_scr(repo_scan_setup):
    handler, scr_runner, postgres, state_store = repo_scan_setup

    async def fake_acquisition(scan_id, input):
        return AcquisitionResult(files=["vuln.py"], archive_path="/tmp/fake")

    with patch.object(scr_runner._acquisition, "run", side_effect=fake_acquisition):
        workflow_id = await handler.handle(
            workflow_name="code-review-only",
            client_id="meridian-financial",
            source="manual_frontend",
            repo_url="https://github.com/snoopysecurity/Broken-Vulnerable-Code-Snippets",
            repo_ref="master",
            context={"repo_auth_token": "fake-token", "connection_id": "test-conn"},
        )
        await asyncio.sleep(0.05)

    snapshot = postgres.rows[workflow_id]["snapshot"]
    assert "scr" in snapshot
    assert "cma" in snapshot
    assert "reporting" in snapshot
    assert snapshot["_workflow_name"] == "code-review-only"

    state = await state_store.load(workflow_id)
    assert state is not None
    assert state.status == "COMPLETED"
    assert state.agent_states["scr"] == "DONE"


@pytest.mark.asyncio
async def test_finalize_heuristic_scr_placeholder_without_state(repo_scan_setup):
    handler, _, postgres, state_store = repo_scan_setup
    shared = SharedMemoryClient(state_store._redis)  # noqa: SLF001
    finalizer = WorkflowFinalizer(shared, postgres, InMemoryKafka(), state_store)
    workflow_id = "WF-heuristic"

    await shared.write_agent_output(workflow_id, "cma", {"agent_id": "cma", "risk_score": 10})
    await shared.write_agent_output(workflow_id, "reporting", {"agent_id": "reporting", "risk_score": 10})

    await finalizer.finalize(workflow_id, "client-1")
    assert postgres.rows[workflow_id]["snapshot"]["scr"]["scan_status"] == "FAILED"
