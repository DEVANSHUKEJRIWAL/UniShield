"""Tests for SCRRunner."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from fakeredis import aioredis as fakeredis
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.output.structured import StructuredOutput
from pydantic import BaseModel

from unishield.agents.scr.schemas.input_schema import SCRAgentInput, ScanMode, TriggerSource
from unishield.agents.scr.schemas.output_schema import SCRAgentOutput
from unishield.agents.scr.scr_runner import SCRRunner
from unishield.agents.scr.stages.stage3_analysis import AnalysisStage
from unishield.infrastructure.model_router import ModelRouter
from unishield.memory.personal_memory import PersonalMemoryClient
from unishield.memory.shared_memory import SharedMemoryClient


class InMemoryKafka:
    async def publish(self, topic: str, payload: dict, key: str | None = None) -> None:
        pass


@pytest_asyncio.fixture
async def redis_client():
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def runner(redis_client):
    config = ClientConfig(mock_mode=True)
    personal = PersonalMemoryClient(redis_client)
    shared = SharedMemoryClient(redis_client)
    return SCRRunner(config, shared, personal, InMemoryKafka(), model_router=ModelRouter(
        __import__("unishield.config.settings", fromlist=["settings"]).settings
    )), personal, shared


def _input(**kwargs) -> SCRAgentInput:
    defaults = {
        "request_id": "scan-1",
        "client_id": "client-1",
        "workflow_id": "wf-1",
        "triggered_by": TriggerSource.MANUAL,
        "scan_mode": ScanMode.FULL_REPO,
        "file_paths": [
            "src/auth/login.py",
            "src/vulnerable_sql.py",
            "tests/test_auth.py",
        ],
        "crown_jewels": ["src/auth/"],
    }
    defaults.update(kwargs)
    return SCRAgentInput(**defaults)


@pytest.mark.asyncio
async def test_checkpoint_resume(runner, redis_client):
    _, personal, _ = runner
    await personal.save_scan_progress("scan-1", 10, ["batch-0", "batch-1", "batch-2"], [], "batch-2")
    progress = await personal.load_scan_progress("scan-1")
    assert progress["current_batch_id"] == "batch-2"
    completed = set(progress["completed_batches"])
    assert "batch-3" not in completed


@pytest.mark.asyncio
async def test_dedup_fingerprinting(runner):
    _, personal, _ = runner
    finding = {
        "file_path": "src/vulnerable_sql.py",
        "line_start": 10,
        "category": "injection",
        "code_snippet": "SELECT",
    }
    fp = AnalysisStage.fingerprint_finding(finding)
    await personal.add_fingerprint("scan-dedup", fp)
    await personal.append_findings("scan-dedup", "b0", [finding], [], [])
    await personal.append_findings("scan-dedup", "b1", [finding], [], [])
    all_f = await personal.load_all_findings("scan-dedup")
    seen = {AnalysisStage.fingerprint_finding(f) for f in all_f["code"]}
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_ioc_enrichment(runner):
    r, personal, shared = runner
    await shared.write_agent_output("wf-ioc", "web", {"ioc_list": ["evil-domain.com"]})
    finding = {
        "file_path": "src/api.py",
        "line_start": 5,
        "code_snippet": "http://evil-domain.com/exfil",
        "severity": "MEDIUM",
        "category": "network",
    }
    await personal.append_findings("scan-ioc", "b0", [finding], [], [])
    from unishield.agents.scr.stages.stage8_threat_intel import ThreatIntelStage
    stage = ThreatIntelStage(personal, shared)
    await stage.run("scan-ioc", _input(workflow_id="wf-ioc", request_id="scan-ioc"))
    all_f = await personal.load_all_findings("scan-ioc")
    assert any(f.get("severity") == "CRITICAL" for f in all_f["code"])


@pytest.mark.asyncio
async def test_priority_queue_order(runner):
    r, _, _ = runner
    files = ["tests/test_utils.py", "src/auth/login.py", "vendor/lib.py"]
    ordered = r._sort_by_priority(files, _input(crown_jewels=["src/auth/"]))
    assert ordered[0] == "src/auth/login.py"


@pytest.mark.asyncio
async def test_repo_scan_fails_when_acquisition_returns_no_files(runner):
    from unittest.mock import patch

    from unishield.agents.scr.tools.repo_acquirer import AcquisitionResult

    scr_runner, _, shared = runner

    async def empty_acquisition(scan_id, input):
        return AcquisitionResult(files=[])

    with patch.object(scr_runner._acquisition, "run", side_effect=empty_acquisition):
        with pytest.raises(RuntimeError, match="0 scannable files"):
            await scr_runner.run(
                _input(
                    file_paths=[],
                    repo_url="https://github.com/o/r",
                    repo_ref="main",
                    repo_auth_token="token",
                )
            )

    output = await shared.read_agent_output("wf-1", "scr")
    assert output["scan_status"] == "FAILED"
    assert "0 scannable files" in output["error_message"]


@pytest.mark.asyncio
async def test_structured_output_parsing():
    class SampleOut(BaseModel):
        status: str
        count: int

    class FakeAgent:
        async def execute(self, query: str):
            from openclaw_sdk.core.types import ExecutionResult
            return ExecutionResult(success=True, content='{"status":"ok","count":3}', latency_ms=1)

    result = await StructuredOutput.execute(FakeAgent(), "test", SampleOut)
    assert result.status == "ok"
    assert result.count == 3
