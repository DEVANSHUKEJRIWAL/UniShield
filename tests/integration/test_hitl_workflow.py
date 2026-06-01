"""HITL queue and investigation note tests."""

import os
import uuid

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
async def test_hitl_queue_db_fallback() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client)
        resp = await client.get(
            "/api/v1/hitl/queue/meridian-financial",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    assert items[0]["action_id"].startswith("hitl-")


@pytest.mark.asyncio
async def test_investigation_add_note() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client)
        cases = await client.get(
            "/api/v1/investigation/cases/meridian-financial",
            headers={"Authorization": f"Bearer {token}"},
        )
        case_id = cases.json()[0]["id"]
        resp = await client.post(
            f"/api/v1/investigation/{case_id}/notes",
            headers={"Authorization": f"Bearer {token}"},
            json={"note": "Analyst verified credential exposure scope"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "note_added"
        assert any(n["text"] == "Analyst verified credential exposure scope" for n in data["notes"])

        case = await client.get(
            f"/api/v1/investigation/{case_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        notes = case.json().get("notes", [])
        assert any(n["text"] == "Analyst verified credential exposure scope" for n in notes)


@pytest.mark.asyncio
async def test_hitl_decide_removes_from_queue() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client)
        queue = await client.get(
            "/api/v1/hitl/queue/meridian-financial",
            headers={"Authorization": f"Bearer {token}"},
        )
        items = queue.json()
        if not items:
            pytest.skip("No HITL items")
        action_id = items[0]["action_id"]
        alert_id = items[0]["action"]["alert_id"]
        resp = await client.post(
            f"/api/v1/hitl/{action_id}/decide?client_id=meridian-financial",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "decision": "accept",
                "original": items[0]["action"],
            },
        )
        assert resp.status_code == 200
        queue2 = await client.get(
            "/api/v1/hitl/queue/meridian-financial",
            headers={"Authorization": f"Bearer {token}"},
        )
        remaining_ids = {i["action"]["alert_id"] for i in queue2.json()}
        assert alert_id not in remaining_ids
