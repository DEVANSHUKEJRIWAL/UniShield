"""Tests for SCR pipeline fixes."""

from __future__ import annotations

import pytest

from backend.cma.cma_runner import CMARunner
from backend.reporting.reporting_runner import _dedupe_critical_count
from backend.scr.tools.sast_runner_heuristics import PathHeuristicScanner
from backend.scr.tools.scanner_integration import is_excluded_secret_path


def test_rce_path_segment_no_false_positive_on_resources():
    scanner = PathHeuristicScanner()
    assert scanner.check_path("razorpay/resources/payment.py", "rce") is False
    assert scanner.check_path("razorpay/rce/payload.py", "rce") is True


def test_secret_path_exclusions():
    assert is_excluded_secret_path("tests/mocks/fake_product.json") is True
    assert is_excluded_secret_path("src/auth/token.py") is False


def test_reporting_dedupe_critical_count():
    scr = {
        "critical_count": 28,
        "top_findings": [
            {"finding_id": "a", "severity": "CRITICAL"},
            {"finding_id": "b", "severity": "HIGH"},
        ],
    }
    cma = {
        "critical_count": 28,
        "top_findings": [
            {"finding_id": "a", "severity": "CRITICAL"},
        ],
    }
    assert _dedupe_critical_count(scr, cma) == 1


@pytest.mark.asyncio
async def test_cma_frameworks_assessed_is_list(monkeypatch):
    from fakeredis import aioredis as fakeredis

    from backend.memory.shared_memory import SharedMemoryClient

    redis = fakeredis.FakeRedis(decode_responses=True)
    shared = SharedMemoryClient(redis)
    await shared.write_agent_output(
        "wf-cma",
        "scr",
        {
            "risk_score": 50,
            "highest_severity": "HIGH",
            "critical_count": 1,
            "secret_findings_count": 0,
            "top_findings": [{"finding_id": "x", "severity": "HIGH", "category": "injection", "file_path": "a.py"}],
        },
    )
    runner = CMARunner(shared)
    await runner.run("wf-cma", "client-1")
    out = await shared.read_agent_output("wf-cma", "cma")
    assert isinstance(out["frameworks_assessed"], list)
    assert isinstance(out["compliance_gaps"], list)
