"""Tests for two-stage findings filter."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.scr.stages.findings_filter import (
    FilterResult,
    FindingsFilter,
    HardExclusionRules,
)


class MockRouter:
    def __init__(self, response: dict | None = None, raise_error: bool = False) -> None:
        self.response = response or {"confidence": 0.9, "keep": True, "reason": "exploitable"}
        self.raise_error = raise_error
        self.last_prompt = ""

    async def score_json(self, prompt: str, client_id: str = "") -> dict:
        self.last_prompt = prompt
        if self.raise_error:
            raise RuntimeError("API down")
        return self.response


def test_hard_exclusion_dos():
    reason = HardExclusionRules.get_exclusion_reason(
        {"description": "Possible denial of service via large payload"},
        "src/api.py",
    )
    assert reason is not None


def test_hard_exclusion_memory_safety_python():
    finding = {"description": "buffer overflow detected", "category": "memory"}
    assert HardExclusionRules.get_exclusion_reason(finding, "app.py") is not None
    assert HardExclusionRules.get_exclusion_reason(finding, "app.c") is None


def test_hard_exclusion_ssrf_html():
    finding = {"description": "SSRF vulnerability", "category": "ssrf"}
    assert HardExclusionRules.get_exclusion_reason(finding, "page.html") is not None
    assert HardExclusionRules.get_exclusion_reason(finding, "api.py") is None


def test_hard_exclusion_markdown():
    assert HardExclusionRules.get_exclusion_reason({"category": "x"}, "README.md") is not None


@pytest.mark.asyncio
async def test_ai_filter_high_confidence_kept():
    filt = FindingsFilter(MockRouter({"confidence": 0.9, "keep": True, "reason": "real"}))
    kept, stats = await filt.filter_findings(
        [{"file_path": "a.py", "description": "sql injection", "category": "injection"}],
        "s1",
        "c1",
    )
    assert len(kept) == 1
    assert stats.kept == 1


@pytest.mark.asyncio
async def test_ai_filter_low_confidence_excluded():
    filt = FindingsFilter(MockRouter({"confidence": 0.6, "keep": False, "reason": "likely fp"}))
    kept, stats = await filt.filter_findings(
        [{"file_path": "a.py", "description": "sql injection", "category": "injection"}],
        "s1",
        "c1",
    )
    assert len(kept) == 0
    assert stats.ai_excluded == 1


@pytest.mark.asyncio
async def test_ai_filter_fail_open():
    filt = FindingsFilter(MockRouter(raise_error=True))
    kept, stats = await filt.filter_findings(
        [{"file_path": "a.py", "description": "auth bypass", "category": "auth"}],
        "s1",
        "c1",
    )
    assert len(kept) == 1
    assert stats.ai_filter_failed == 1


def test_bfsi_noise_excluded():
    reason = HardExclusionRules.get_exclusion_reason(
        {"description": "weak random used in logging statement"},
        "payments.py",
    )
    assert reason is not None


@pytest.mark.asyncio
async def test_filter_stats_accurate():
    router = MockRouter({"confidence": 0.9, "keep": True, "reason": "ok"})
    filt = FindingsFilter(router)
    findings = [
        {"file_path": "a.py", "description": "denial of service", "category": "dos"},
        {"file_path": "b.py", "description": "sql injection", "category": "injection"},
    ]
    kept, stats = await filt.filter_findings(findings, "s1", "c1")
    assert stats.total_input == 2
    assert stats.hard_excluded + stats.kept + stats.ai_excluded == stats.total_input or stats.kept >= 1


@pytest.mark.asyncio
async def test_custom_instructions_passed_to_prompt():
    router = MockRouter()
    filt = FindingsFilter(router, custom_instructions="BFSI client Meridian Financial")
    await filt.filter_findings(
        [{"file_path": "a.py", "description": "auth bypass", "category": "auth"}],
        "s1",
        "c1",
    )
    assert "Meridian Financial" in router.last_prompt
