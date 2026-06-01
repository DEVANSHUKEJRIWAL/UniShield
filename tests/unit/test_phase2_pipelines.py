"""Phase 2 pipeline tests with mocked external calls."""

from unittest.mock import AsyncMock, patch

import pytest

from packages.phase2.dark_web import run_dark_web_scan
from packages.phase2.insider import run_insider_scan
from packages.phase2.source_code import run_mythos_review


@pytest.mark.asyncio
async def test_dark_web_scan_returns_findings() -> None:
    with patch(
        "packages.integrations.hibp.fetch_hibp_breaches",
        new_callable=AsyncMock,
        return_value={"live": False, "exposed_count": 0, "breach_names": []},
    ):
        result = await run_dark_web_scan("meridian.com", "meridian", "banking")
    assert "findings" in result
    assert "summary" in result
    assert result["summary"]["total"] >= 1


@pytest.mark.asyncio
async def test_mythos_review_mock_sast() -> None:
    result = await run_mythos_review("", "python", "app.py", "banking", repo_path="/workspace")
    assert "findings" in result
    assert result["summary"]["total"] >= 1


@pytest.mark.asyncio
async def test_insider_scan_rule_engine() -> None:
    events = [
        {"type": "login", "timestamp": "2024-11-01T23:00:00+00:00", "country": "RU", "user_id": "alice"},
        {"type": "privilege_change", "user_id": "alice"},
    ]
    result = await run_insider_scan("meridian-financial", "banking", "alice", events)
    assert result["summary"]["topRiskScore"] >= 35
    assert len(result["findings"]) >= 1
    assert result["findings"][0]["kind"] == "insider-threat"
