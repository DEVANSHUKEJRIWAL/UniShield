"""Tests for the orchestrator."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fakeredis import aioredis as fakeredis

from unishield.memory.shared_memory import SharedMemoryClient
from unishield.orchestrator.decision_engine import DecisionEngine
from unishield.orchestrator.finalizer import DataIntegrityError, WorkflowFinalizer
from unishield.orchestrator.orchestrator import Orchestrator
from unishield.orchestrator.workflow_definitions import WORKFLOW_DEFINITIONS
from unishield.orchestrator.workflow_state import WorkflowStateStore
from unishield.schemas.decision_surface import AgentDecisionSurface
from unishield.schemas.workflow_schemas import AgentCompleteEvent, TriggerSource, WorkflowTrigger


class InMemoryKafka:
    """Simple in-memory Kafka mock."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, dict, str | None]] = []
        self._started = False

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def publish(self, topic: str, payload: dict, key: str | None = None) -> None:
        self.messages.append((topic, payload, key))


class MockPostgres:
    """In-memory PostgreSQL mock."""

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}
        self.execute_calls = 0

    async def execute(self, query: str, *args) -> str:
        self.execute_calls += 1
        workflow_id, client_id, snapshot, checksum, completed_at = args
        self.rows[workflow_id] = {
            "workflow_id": workflow_id,
            "client_id": client_id,
            "snapshot": snapshot,
            "checksum": checksum,
            "completed_at": completed_at,
        }
        return "INSERT 1"

    async def fetchrow(self, query: str, *args) -> dict | None:
        workflow_id = args[0]
        row = self.rows.get(workflow_id)
        if row:
            return {"checksum": row["checksum"]}
        return None


@pytest_asyncio.fixture
async def redis_client():
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def orchestrator_setup(redis_client):
    kafka = InMemoryKafka()
    await kafka.start()
    shared = SharedMemoryClient(redis_client)
    state_store = WorkflowStateStore(redis_client)
    decision_engine = DecisionEngine()
    postgres = MockPostgres()
    finalizer = WorkflowFinalizer(shared, postgres, kafka, state_store)
    orch = Orchestrator(kafka, shared, state_store, decision_engine, finalizer)
    return orch, kafka, shared, state_store, postgres


def _surface(
    agent_id: str,
    risk_score: int = 50,
    secret_findings_count: int = 0,
    correlated_to_incident: bool = False,
    requires_human_approval: bool = False,
    kill_chain_stage: int | None = None,
) -> AgentDecisionSurface:
    return AgentDecisionSurface(
        agent_id=agent_id,
        completed_at=datetime.now(UTC),
        risk_score=risk_score,
        highest_severity="HIGH" if risk_score >= 50 else "LOW",
        requires_human_approval=requires_human_approval,
        auto_remediation_safe=risk_score < 50,
        forward_to=[],
        critical_count=0,
        secret_findings_count=secret_findings_count,
        correlated_to_incident=correlated_to_incident,
        kill_chain_stage=kill_chain_stage,
    )


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
    assert state is not None
    assert state.flow_type == "fixed"
    assert state.current_step_index == 0

    triggered_agents = [agent for wf, agent, _prio in orch.trigger_log if wf == workflow_id]
    assert triggered_agents == ["UniShield-SCR"]

    scr_topics = [topic for topic, payload, _key in kafka.messages if payload.get("agent_id") == "UniShield-SCR"]
    assert len(scr_topics) >= 1


@pytest.mark.asyncio
async def test_dynamic_routing_high_risk(orchestrator_setup):
    orch, kafka, shared, state_store, _ = orchestrator_setup

    trigger = WorkflowTrigger(
        workflow_name="incident-response",
        client_id="client-1",
        source=TriggerSource.INCIDENT,
    )
    workflow_id = await orch.start_workflow(trigger)

    surface = _surface("UniShield-SCR", risk_score=87)
    await _write_surface(shared, workflow_id, surface)

    event = AgentCompleteEvent(
        workflow_id=workflow_id,
        agent_id="UniShield-SCR",
        client_id="client-1",
        correlation_id=workflow_id,
        status="SUCCESS",
        completed_at=datetime.now(UTC),
    )
    await orch.on_agent_complete(event)

    triggered = [a for w, a, _p in orch.trigger_log if w == workflow_id and a in ("UniShield-AF", "UniShield-CMA")]
    assert "UniShield-AF" in triggered
    assert "UniShield-CMA" in triggered


@pytest.mark.asyncio
async def test_dynamic_routing_low_risk(orchestrator_setup):
    orch, kafka, shared, state_store, _ = orchestrator_setup

    trigger = WorkflowTrigger(
        workflow_name="incident-response",
        client_id="client-1",
        source=TriggerSource.INCIDENT,
    )
    workflow_id = await orch.start_workflow(trigger)

    surface = _surface("UniShield-SCR", risk_score=40)
    await _write_surface(shared, workflow_id, surface)

    event = AgentCompleteEvent(
        workflow_id=workflow_id,
        agent_id="UniShield-SCR",
        client_id="client-1",
        correlation_id=workflow_id,
        status="SUCCESS",
        completed_at=datetime.now(UTC),
    )
    await orch.on_agent_complete(event)

    triggered = [a for w, a, _p in orch.trigger_log if w == workflow_id]
    assert "UniShield-Reporting" in triggered
    assert "UniShield-AF" not in triggered


@pytest.mark.asyncio
async def test_mid_flow_escalation(orchestrator_setup):
    orch, _, shared, state_store, _ = orchestrator_setup

    trigger = WorkflowTrigger(
        workflow_name="code-review-only",
        client_id="client-1",
        source=TriggerSource.MANUAL_FRONTEND,
        context={"threat_actor_ttps": ["T1059"], "matched_ttps": ["T1059"]},
    )
    workflow_id = await orch.start_workflow(trigger)

    surface = _surface("UniShield-SCR", risk_score=60, correlated_to_incident=True)
    await _write_surface(shared, workflow_id, surface)

    event = AgentCompleteEvent(
        workflow_id=workflow_id,
        agent_id="UniShield-SCR",
        client_id="client-1",
        correlation_id=workflow_id,
        status="SUCCESS",
        completed_at=datetime.now(UTC),
    )
    await orch.on_agent_complete(event)

    state = await state_store.load(workflow_id)
    assert state.escalated_to_dynamic is True
    assert state.flow_type == "dynamic"


@pytest.mark.asyncio
async def test_human_gate_pause(orchestrator_setup):
    orch, kafka, shared, state_store, _ = orchestrator_setup

    trigger = WorkflowTrigger(
        workflow_name="incident-response",
        client_id="client-1",
        source=TriggerSource.INCIDENT,
    )
    workflow_id = await orch.start_workflow(trigger)

    surface = _surface("UniShield-Reporting", requires_human_approval=True)
    await _write_surface(shared, workflow_id, surface)

    state = await state_store.load(workflow_id)
    state.escalated_to_dynamic = True
    state.flow_type = "dynamic"
    await state_store.save(state)

    event = AgentCompleteEvent(
        workflow_id=workflow_id,
        agent_id="UniShield-Reporting",
        client_id="client-1",
        correlation_id=workflow_id,
        status="SUCCESS",
        completed_at=datetime.now(UTC),
    )
    await orch.on_agent_complete(event)

    state = await state_store.load(workflow_id)
    assert state.paused is True
    assert state.status == "PAUSED"

    gate_events = [p for t, p, k in kafka.messages if t == "workflow.human_gate"]
    assert len(gate_events) >= 1


@pytest.mark.asyncio
async def test_human_gate_approve(orchestrator_setup):
    orch, _, shared, state_store, _ = orchestrator_setup

    trigger = WorkflowTrigger(
        workflow_name="code-review-only",
        client_id="client-1",
        source=TriggerSource.MANUAL_FRONTEND,
    )
    workflow_id = await orch.start_workflow(trigger)

    state = await state_store.load(workflow_id)
    await state_store.pause(workflow_id, "Awaiting approval", 4)

    await orch.approve_workflow(workflow_id, "ciso@example.com")

    state = await state_store.load(workflow_id)
    assert state.paused is False
    assert state.status == "RUNNING"
    assert state.approved_by == "ciso@example.com"


@pytest.mark.asyncio
async def test_finalize_clears_redis_after_db(orchestrator_setup, redis_client):
    orch, kafka, shared, state_store, postgres = orchestrator_setup

    workflow_id = "wf-finalize-test"
    await shared.write_agent_output(workflow_id, "UniShield-SCR", {"risk_score": 10})
    assert await shared.workflow_exists(workflow_id)

    finalizer = WorkflowFinalizer(shared, postgres, kafka, state_store)
    await finalizer.finalize(workflow_id, "client-1")

    assert not await shared.workflow_exists(workflow_id)
    assert postgres.execute_calls >= 1
    completed_events = [p for t, p, k in kafka.messages if t == "workflow.completed"]
    assert len(completed_events) == 1


@pytest.mark.asyncio
async def test_finalize_checksum_mismatch_raises(orchestrator_setup):
    _, kafka, shared, state_store, postgres = orchestrator_setup

    workflow_id = "wf-bad-checksum"
    await shared.write_agent_output(workflow_id, "UniShield-SCR", {"data": "test"})

    async def bad_fetchrow(query, *args):
        return {"checksum": "wrong-checksum"}

    postgres.fetchrow = bad_fetchrow

    finalizer = WorkflowFinalizer(shared, postgres, kafka, state_store)
    with pytest.raises(DataIntegrityError):
        await finalizer.finalize(workflow_id, "client-1")

    assert await shared.workflow_exists(workflow_id)
