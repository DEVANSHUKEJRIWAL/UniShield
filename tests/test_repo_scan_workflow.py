"""End-to-end workflow tests for repo-connected code review scans."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import pytest_asyncio
from fakeredis import aioredis as fakeredis
from openclaw_sdk.core.config import ClientConfig

from backend.cma.cma_runner import CMARunner
from backend.reporting.reporting_runner import ReportingRunner
from backend.scr.tools.repo_acquirer import AcquisitionResult
from backend.scr.scr_runner import SCRRunner
from backend.infrastructure.model_router import ModelRouter
from backend.config.settings import settings
from backend.memory.personal_memory import PersonalMemoryClient
from backend.memory.shared_memory import SharedMemoryClient
from backend.orchestrator.decision_engine import DecisionEngine
from backend.orchestrator.finalizer import WorkflowFinalizer
from backend.orchestrator.orchestrator import Orchestrator
from backend.orchestrator.trigger_handler import TriggerHandler
from backend.orchestrator.workflow_state import WorkflowStateStore
from backend.schemas.workflow_schemas import TriggerSource, WorkflowTrigger


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
    test_settings = settings.model_copy(update={"scr_require_tools": False})
    scr_runner = SCRRunner(
        config, shared, personal, kafka, test_settings, ModelRouter(test_settings)
    )
    cma_runner = CMARunner(shared)
    reporting_runner = ReportingRunner(shared)
    orch = Orchestrator(
        config,
        shared,
        state_store,
        DecisionEngine(),
        finalizer,
        kafka,
        test_settings,
        scr_runner,
        cma_runner=cma_runner,
        reporting_runner=reporting_runner,
    )
    handler = TriggerHandler(orch)
    return handler, scr_runner, postgres, state_store, orch


@pytest.mark.asyncio
async def test_repo_scan_code_review_includes_scr(repo_scan_setup):
    _, scr_runner, postgres, state_store, orch = repo_scan_setup

    async def fake_acquisition(scan_id, input):
        return AcquisitionResult(files=["vuln.py"], archive_path="/tmp/fake")

    with patch.object(scr_runner._acquisition, "run", side_effect=fake_acquisition):
        workflow_id = await orch.start_workflow(
            WorkflowTrigger(
                workflow_name="code-review-only",
                client_id="meridian-financial",
                source=TriggerSource.MANUAL_FRONTEND,
                repo_url="https://github.com/snoopysecurity/Broken-Vulnerable-Code-Snippets",
                repo_ref="master",
                context={"repo_auth_token": "fake-token", "connection_id": "test-conn"},
            ),
            run_inline=True,
        )

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
    _, _, postgres, state_store, _ = repo_scan_setup
    shared = SharedMemoryClient(state_store._redis)  # noqa: SLF001
    finalizer = WorkflowFinalizer(shared, postgres, InMemoryKafka(), state_store)
    workflow_id = "WF-heuristic"

    await shared.write_agent_output(workflow_id, "cma", {"agent_id": "cma", "risk_score": 10})
    await shared.write_agent_output(workflow_id, "reporting", {"agent_id": "reporting", "risk_score": 10})

    await finalizer.finalize(workflow_id, "client-1")
    assert postgres.rows[workflow_id]["snapshot"]["scr"]["scan_status"] == "FAILED"
