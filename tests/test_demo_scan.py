"""Tests for demo scan workflow trigger."""

from __future__ import annotations

import asyncio
from pathlib import Path
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
from backend.scr.scr_progress import ScrProgressTracker


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
async def demo_setup():
    redis = fakeredis.FakeRedis(decode_responses=True)
    shared = SharedMemoryClient(redis)
    personal = PersonalMemoryClient(redis)
    state_store = WorkflowStateStore(redis)
    kafka = InMemoryKafka()
    postgres = MockPostgres()
    finalizer = WorkflowFinalizer(shared, postgres, kafka, state_store)
    config = ClientConfig(mock_mode=True)
    test_settings = settings.model_copy(update={"scr_require_tools": False})
    progress = ScrProgressTracker(redis)
    scr_runner = SCRRunner(
        config,
        shared,
        personal,
        kafka,
        test_settings,
        ModelRouter(test_settings),
        progress_tracker=progress,
    )
    orch = Orchestrator(
        config,
        shared,
        state_store,
        DecisionEngine(),
        finalizer,
        kafka,
        test_settings,
        scr_runner,
        cma_runner=CMARunner(shared),
        reporting_runner=ReportingRunner(shared),
    )
    handler = TriggerHandler(orch)
    return handler, scr_runner, postgres, state_store, progress


@pytest.mark.asyncio
async def test_demo_scan_local_workspace(demo_setup):
    handler, scr_runner, postgres, state_store, progress = demo_setup
    root = Path(__file__).resolve().parents[1]
    orch = handler._orchestrator

    async def fake_acquisition(scan_id, input):
        return AcquisitionResult(files=["backend/scr/scr_runner.py"], archive_path=str(root))

    with patch.object(scr_runner._acquisition, "run", side_effect=fake_acquisition):
        workflow_id = await orch.start_workflow(
            WorkflowTrigger(
                workflow_name="code-review-only",
                client_id="meridian-financial",
                source=TriggerSource.MANUAL_FRONTEND,
                context={
                    "archive_path": str(root),
                    "skip_tool_check": True,
                    "scan_mode": "full_repo",
                },
            ),
            run_inline=True,
        )

    snapshot = postgres.rows[workflow_id]["snapshot"]
    assert "scr" in snapshot
    assert snapshot["scr"].get("scan_status") == "COMPLETED"

    prog = await progress.get(workflow_id)
    assert prog is not None
    assert prog["stages"][-1]["status"] == "done"

    state = await state_store.load(workflow_id)
    assert state is not None
    assert state.status == "COMPLETED"
