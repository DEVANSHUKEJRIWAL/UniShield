"""Phase 2 BFSI API integration tests."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("UNISHIELD_USE_SQLITE", "1")

from services.api_gateway.main import app


@pytest.mark.asyncio
async def test_mythos_review_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/mythos-review",
            json={"code": "password = 'secret'", "language": "python", "filename": "bad.py"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "findings" in data
    assert data["summary"]["total"] >= 1


@pytest.mark.asyncio
async def test_darkweb_scan_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/darkweb/scan",
            json={"domain": "meridian.com", "brand": "meridian"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "findings" in data
    assert data["meta"]["domain"] == "meridian.com"


@pytest.mark.asyncio
async def test_insider_scan_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/insider/scan",
            json={
                "user_id": "alice",
                "events": [{"type": "privilege_change", "user_id": "alice", "timestamp": "2024-11-01T23:00:00Z"}],
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "findings" in data
    assert data["summary"]["topRiskScore"] >= 35


@pytest.mark.asyncio
async def test_orchestrator_scan_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/orchestrator/scan",
            json={"domain": "meridian.com", "user_id": "alice"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "darkweb" in data
    assert "source_code" in data
    assert "insider" in data
