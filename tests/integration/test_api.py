"""API integration tests."""

import pytest
from httpx import ASGITransport, AsyncClient

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
    pytest.importorskip("asyncpg")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/login", json={"email": "bad@test.com", "password": "wrong"})
        assert resp.status_code == 401
    except OSError:
        pytest.skip("PostgreSQL not available")
