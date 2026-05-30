"""Findings and dashboard API integration tests (Week 5–6)."""

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
async def test_findings_paginated() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client)
        resp = await client.get(
            "/api/v1/findings/meridian-financial?page=1",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_dashboard_live_kpis() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client)
        resp = await client.get(
            "/api/v1/dashboard/meridian-financial",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "risk_trend" in data
    assert isinstance(data["hitl_queue_depth"], int)


@pytest.mark.asyncio
async def test_csp_header() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
    assert resp.headers.get("content-security-policy")
