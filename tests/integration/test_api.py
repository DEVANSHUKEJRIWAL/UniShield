"""Login integration tests."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

# Use SQLite for tests — no Postgres required
os.environ.setdefault("UNISHIELD_USE_SQLITE", "1")

from services.api_gateway.main import app


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    """Health check returns healthy."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_agent_status_public() -> None:
    """Public agent status lists 13 agents."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/agent/status")
    assert resp.status_code == 200
    assert len(resp.json()["agents"]) == 13


@pytest.mark.asyncio
async def test_login_invalid_credentials() -> None:
    """Login rejects bad credentials."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/login", json={"email": "bad@test.com", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_valid_credentials() -> None:
    """Login succeeds with seeded demo user."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "analyst@meridian.com", "password": "analyst123"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "SOC_ANALYST"
