"""Tests for full 10-stage SCR tooling."""

from __future__ import annotations

import os
import tempfile

import pytest
import pytest_asyncio
from fakeredis import aioredis as fakeredis

from unishield.agents.scr.schemas.input_schema import SCRAgentInput, ScanMode, TriggerSource
from unishield.agents.scr.stages.stage2_detection import DetectionStage
from unishield.agents.scr.stages.stage8_threat_intel import CROWN_JEWEL_RISK_BOOST, ThreatIntelStage
from unishield.agents.scr.tools import scanner_integration as scanners
from unishield.agents.scr.tools.sast_runner_heuristics import HeuristicSAST
from unishield.memory.personal_memory import PersonalMemoryClient
from unishield.memory.shared_memory import SharedMemoryClient


@pytest_asyncio.fixture
async def redis_client():
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def memory_clients(redis_client):
    personal = PersonalMemoryClient(redis_client)
    shared = SharedMemoryClient(redis_client)
    return personal, shared


def test_shannon_entropy_high_for_random_string():
    assert scanners.shannon_entropy("aabbcc") < scanners.shannon_entropy("Kj8#mN2$pQ9@xR4!vL7")


def test_mask_secret():
    assert scanners.mask_secret("short") == "****"
    masked = scanners.mask_secret("sk-abcdefghijklmnopqrstuvwxyz")
    assert "****" in masked
    assert masked.startswith("sk-")


def test_heuristic_php_command_injection():
    h = HeuristicSAST()
    findings = h.analyze_path_hints("PHP/shell.php", "php")
    assert any(f["category"] == "command_injection" for f in findings)


@pytest.mark.asyncio
async def test_detection_framework_markers(redis_client):
    tmp = tempfile.mkdtemp()
    pkg = os.path.join(tmp, "package.json")
    with open(pkg, "w", encoding="utf-8") as f:
        f.write('{"dependencies": {"express": "^4.18.0"}}')
    py = os.path.join(tmp, "app.py")
    with open(py, "w", encoding="utf-8") as f:
        f.write("from flask import Flask\napp = Flask(__name__)\n")

    stage = DetectionStage(PersonalMemoryClient(redis_client))
    result = await stage.run(
        "scan-detect",
        ["app.py", "package.json"],
        archive_path=tmp,
    )
    assert "python" in result["languages"]
    assert "express" in result["frameworks"] or "flask" in result["frameworks"]
    assert "p/python" in result["semgrep_configs"]


@pytest.mark.asyncio
async def test_threat_intel_crown_jewel_risk_boost(memory_clients):
    personal, shared = memory_clients
    finding = {
        "file_path": "src/auth/login.py",
        "line_start": 1,
        "code_snippet": "def login(): pass",
        "severity": "MEDIUM",
        "category": "auth",
    }
    await personal.append_findings("scan-jewel", "b0", [finding], [], [])
    stage = ThreatIntelStage(personal, shared)
    boost = await stage.run(
        "scan-jewel",
        SCRAgentInput(
            request_id="scan-jewel",
            client_id="c1",
            workflow_id="wf-j",
            triggered_by=TriggerSource.MANUAL,
            scan_mode=ScanMode.FULL_REPO,
            crown_jewels=["src/auth/"],
        ),
    )
    assert boost >= CROWN_JEWEL_RISK_BOOST
    all_f = await personal.load_all_findings("scan-jewel")
    assert any(f.get("crown_jewel_boost") for f in all_f["code"])


def test_sbom_summary():
    sbom = {
        "bomFormat": "CycloneDX",
        "components": [{"purl": "pkg:npm/lodash@4.0.0"}, {"purl": "pkg:pypi/requests@2.0"}],
    }
    summary = scanners.sbom_summary(sbom)
    assert summary["components"] == 2
    assert "npm" in summary["ecosystems"]
