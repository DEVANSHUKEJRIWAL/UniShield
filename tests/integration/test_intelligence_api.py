"""Integration tests for intelligence and cloud CSPM APIs."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("UNISHIELD_USE_SQLITE", "1")

from services.api_gateway.main import app


async def _login(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@meridian.com", "password": "analyst123"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_ai_brief_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client)
        resp = await client.get(
            "/api/v1/ai-brief/meridian-financial?range=7d",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "tabs" in data
    assert "exec" in data["tabs"]
    assert "risk_score" in data


@pytest.mark.asyncio
async def test_threat_geo_has_coordinates() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client)
        resp = await client.get(
            "/api/v1/threat-geo/meridian-financial?range=7d",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    origins = resp.json()["origins"]
    assert origins
    assert "lat" in origins[0]
    assert "lng" in origins[0]


@pytest.mark.asyncio
async def test_dashboard_kpi_sparklines() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client)
        resp = await client.get(
            "/api/v1/dashboard/meridian-financial/kpi-sparklines?range=7d",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    spark = resp.json()["sparklines"]
    assert "risk" in spark
    assert len(spark["risk"]) >= 4


@pytest.mark.asyncio
async def test_priority_queue_bfsi_first() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client)
        resp = await client.get(
            "/api/v1/dashboard/meridian-financial/priority-queue?range=30d",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items
    assert any(i.get("bfsi") for i in items)


@pytest.mark.asyncio
async def test_entity_aware_search() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client)
        resp = await client.get(
            "/api/v1/search/meridian-financial?q=CVE-2024-1234",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity"]["type"] == "cve"


@pytest.mark.asyncio
async def test_cspm_scan_persists_findings() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client)
        resp = await client.post(
            "/api/v1/cloud/cspm/scan",
            headers={"Authorization": f"Bearer {token}"},
            json={"client_id": "meridian-financial", "connector": "guardduty"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["events"] >= 1
    assert len(data["persisted_findings"]) >= 1
