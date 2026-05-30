"""Tenant isolation integration tests (Week 8)."""

import pytest
from httpx import ASGITransport, AsyncClient

from packages.core.auth import create_access_token
from services.api_gateway.main import app


@pytest.fixture
def analyst_token():
    return create_access_token(
        {"sub": "u1", "email": "analyst@meridian.com", "role": "SOC_ANALYST", "tenant_id": "meridian-financial"}
    )


@pytest.fixture
def other_tenant_token():
    return create_access_token(
        {"sub": "u2", "email": "analyst@other.com", "role": "SOC_ANALYST", "tenant_id": "other-corp"}
    )


@pytest.mark.asyncio
async def test_cross_tenant_dashboard_denied(analyst_token, other_tenant_token):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        ok = await client.get(
            "/api/v1/dashboard/meridian-financial",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert ok.status_code == 200
        denied = await client.get(
            "/api/v1/dashboard/meridian-financial",
            headers={"Authorization": f"Bearer {other_tenant_token}"},
        )
        assert denied.status_code == 403


@pytest.mark.asyncio
async def test_kg_blast_radius_tenant_isolation(analyst_token, other_tenant_token):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.get(
            "/api/v1/kg/blast-radius/db-prod-01?client_id=meridian-financial",
            headers={"Authorization": f"Bearer {other_tenant_token}"},
        )
        assert denied.status_code == 403
