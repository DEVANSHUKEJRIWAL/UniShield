"""Tests for the OpenClaw-based orchestrator."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from fakeredis import aioredis as fakeredis
from openclaw_sdk.core.config import ClientConfig

from unishield.agents.scr.scr_runner import SCRRunner, normalize_agent_key
from unishield.infrastructure.model_router import ModelRouter
from unishield.memory.personal_memory import PersonalMemoryClient
from unishield.memory.shared_memory import SharedMemoryClient
from unishield.orchestrator.decision_engine import DecisionEngine
from unishield.orchestrator.finalizer import DataIntegrityError, WorkflowFinalizer
from unishield.orchestrator.orchestrator import Orchestrator
from unishield.orchestrator.workflow_state import WorkflowState
from unishield.schemas.decision_surface import AgentDecisionSurface
from unishield.schemas.workflow_schemas import TriggerSource, WorkflowTrigger


class InMemoryKafka:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict, str | None]] = []

    async def publish(self, topic: str, payload: dict, key: str | None = None) -> None:
        self.messages.append((topic, payload, key))


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
async def redis_client():
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def orchestrator_setup(redis_client):
    kafka = InMemoryKafka()
    shared = SharedMemoryClient(redis_client)
    personal = PersonalMemoryClient(redis_client)
    state_store = __import__(
        "unishield.orchestrator.workflow_state", fromlist=["WorkflowStateStore"]
    ).WorkflowStateStore(redis_client)
    decision_engine = DecisionEngine()
    postgres = MockPostgres()
    finalizer = WorkflowFinalizer(shared, postgres, kafka, state_store)
    config = ClientConfig(mock_mode=True)
    model_router = ModelRouter(__import__("unishield.config.settings", fromlist=["settings"]).settings)
    scr_runner = SCRRunner(config, shared, personal, kafka, model_router=model_router)
    orch = Orchestrator(
        config, shared, state_store, decision_engine, finalizer, kafka, scr_runner=scr_runner
    )
    return orch, kafka, shared, state_store, postgres


def _surface(agent_id: str = "scr", **kwargs) -> AgentDecisionSurface:
    defaults = dict(
        agent_id=agent_id,
        completed_at=datetime.now(UTC),
        risk_score=50,
        highest_severity="MEDIUM",
        requires_human_approval=False,
        auto_remediation_safe=True,
        forward_to=[],
        critical_count=0,
        secret_findings_count=0,
        correlated_to_incident=False,
    )
    defaults.update(kwargs)
    return AgentDecisionSurface(**defaults)


async def _write_surface(shared: SharedMemoryClient, workflow_id: str, surface: AgentDecisionSurface) -> None:
    await shared.write_agent_output(
        workflow_id,
        surface.agent_id,
        {
            "agent_id": surface.agent_id,
            "completed_at": surface.completed_at.isoformat(),
            "risk_score": surface.risk_score,
            "highest_severity": surface.highest_severity,
            "requires_human_approval": surface.requires_human_approval,
            "auto_remediation_safe": surface.auto_remediation_safe,
            "forward_to": surface.forward_to,
            "critical_count": surface.critical_count,
            "secret_findings_count": surface.secret_findings_count,
            "correlated_to_incident": surface.correlated_to_incident,
            "kill_chain_stage": surface.kill_chain_stage,
        },
    )


@pytest.mark.asyncio
async def test_fixed_workflow_trigger(orchestrator_setup):
    orch, kafka, _, state_store, _ = orchestrator_setup
    trigger = WorkflowTrigger(
        workflow_name="code-review-only",
        client_id="client-1",
        source=TriggerSource.MANUAL_FRONTEND,
    )
    workflow_id = await orch.start_workflow(trigger)
    state = await state_store.load(workflow_id)
    assert state.flow_type == "fixed"
    triggered = [a for wf, a, _ in orch.trigger_log if wf == workflow_id]
    assert "unishield-scr" in triggered
    started = [t for t, _, _ in kafka.messages if t == "workflow.started"]
    assert len(started) >= 1


@pytest.mark.asyncio
async def test_dynamic_routing_high_risk(orchestrator_setup):
    orch, _, shared, state_store, _ = orchestrator_setup
    trigger = WorkflowTrigger(
        workflow_name="incident-response",
        client_id="client-1",
        source=TriggerSource.INCIDENT,
    )
    workflow_id = await orch.start_workflow(trigger)
    await _write_surface(shared, workflow_id, _surface(risk_score=87))
    await orch.on_agent_complete({"workflow_id": workflow_id, "agent_id": "unishield-scr"})
    triggered = [a for wf, a, _ in orch.trigger_log if wf == workflow_id]
    assert "unishield-af" in triggered
    assert "unishield-cma" in triggered


@pytest.mark.asyncio
async def test_dynamic_routing_low_risk(orchestrator_setup):
    orch, _, shared, _, _ = orchestrator_setup
    workflow_id = await orch.start_workflow(
        WorkflowTrigger("incident-response", "client-1", TriggerSource.INCIDENT)
    )
    await _write_surface(shared, workflow_id, _surface(risk_score=40))
    await orch.on_agent_complete({"workflow_id": workflow_id, "agent_id": "scr"})
    triggered = [a for wf, a, _ in orch.trigger_log if wf == workflow_id]
    assert "unishield-reporting" in triggered


@pytest.mark.asyncio
async def test_mid_flow_escalation(orchestrator_setup):
    orch, _, shared, state_store, _ = orchestrator_setup
    workflow_id = await orch.start_workflow(
        WorkflowTrigger("code-review-only", "client-1", TriggerSource.MANUAL_FRONTEND)
    )
    await _write_surface(shared, workflow_id, _surface(correlated_to_incident=True))
    await orch.on_agent_complete({"workflow_id": workflow_id, "agent_id": "scr"})
    state = await state_store.load(workflow_id)
    assert state.escalated_to_dynamic is True


@pytest.mark.asyncio
async def test_human_gate_pause(orchestrator_setup):
    orch, kafka, shared, state_store, _ = orchestrator_setup
    workflow_id = await orch.start_workflow(
        WorkflowTrigger("incident-response", "c1", TriggerSource.INCIDENT)
    )
    state = await state_store.load(workflow_id)
    state.escalated_to_dynamic = True
    state.flow_type = "dynamic"
    await state_store.save(state)
    await _write_surface(shared, workflow_id, _surface(agent_id="reporting", requires_human_approval=True))
    await orch.on_agent_complete({"workflow_id": workflow_id, "agent_id": "reporting"})
    state = await state_store.load(workflow_id)
    assert state.paused is True
    assert any(t == "workflow.human_gate" for t, _, _ in kafka.messages)


@pytest.mark.asyncio
async def test_finalize_verifies_checksum(orchestrator_setup, redis_client):
    _, kafka, shared, state_store, postgres = orchestrator_setup
    workflow_id = "WF-test01"
    await shared.write_agent_output(workflow_id, "scr", {"risk_score": 10})
    finalizer = WorkflowFinalizer(shared, postgres, kafka, state_store)
    await finalizer.finalize(workflow_id, "client-1")
    assert not await shared.workflow_exists(workflow_id)


@pytest.mark.asyncio
async def test_finalize_checksum_mismatch_raises(orchestrator_setup):
    _, kafka, shared, state_store, postgres = orchestrator_setup
    workflow_id = "WF-bad"
    await shared.write_agent_output(workflow_id, "scr", {"x": 1})

    async def bad_fetchrow(query, *args):
        return {"checksum": "wrong"}

    postgres.fetchrow = bad_fetchrow
    finalizer = WorkflowFinalizer(shared, postgres, kafka, state_store)
    with pytest.raises(DataIntegrityError):
        await finalizer.finalize(workflow_id, "client-1")


@pytest.mark.asyncio
async def test_finalize_adds_scr_placeholder_when_missing(orchestrator_setup):
    _, kafka, shared, state_store, postgres = orchestrator_setup
    workflow_id = "WF-noscr"
    await shared.write_agent_output(workflow_id, "cma", {"risk_score": 10, "agent_id": "cma"})
    state = WorkflowState(
        workflow_id=workflow_id,
        client_id="client-1",
        incident_id=None,
        workflow_name="code-review-only",
        flow_type="fixed",
        triggered_by="manual_frontend",
        started_at=datetime.now(UTC),
        agent_states={"scr": "FAILED", "cma": "DONE", "reporting": "DONE"},
        current_step_index=2,
    )
    await state_store.save(state)
    finalizer = WorkflowFinalizer(shared, postgres, kafka, state_store)
    await finalizer.finalize(workflow_id, "client-1")
    assert "scr" in postgres.rows[workflow_id]["snapshot"]
    assert postgres.rows[workflow_id]["snapshot"]["scr"]["scan_status"] == "FAILED"


def test_normalize_agent_key():
    assert normalize_agent_key("UniShield-SCR") == "scr"
    assert normalize_agent_key("unishield-scr") == "scr"
