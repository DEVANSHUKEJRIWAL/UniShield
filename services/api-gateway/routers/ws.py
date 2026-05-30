"""WebSocket real-time event streaming."""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from packages.core.redis_client import read_stream
from packages.shared_types.constants import RedisStream

router = APIRouter(tags=["websocket"])

connections: dict[str, list[WebSocket]] = {}


@router.websocket("/api/v1/ws/{client_id}")
async def tenant_event_stream(websocket: WebSocket, client_id: str) -> None:
    """Real-time event stream per tenant."""
    await websocket.accept()
    if client_id not in connections:
        connections[client_id] = []
    connections[client_id].append(websocket)
    last_id = "0"
    try:
        while True:
            entries = await read_stream(RedisStream.EVENTS_NORMALISED, last_id, count=10, block_ms=3000)
            for msg_id, data in entries:
                last_id = msg_id
                if data.get("tenant_id") == client_id:
                    await websocket.send_json(data)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        connections[client_id].remove(websocket)


@router.websocket("/api/v1/agents/stream/{client_id}")
async def agent_output_stream(websocket: WebSocket, client_id: str) -> None:
    """Live agent output stream."""
    await websocket.accept()
    await websocket.send_json({"status": "connected", "client_id": client_id})
    last_ids: dict[str, str] = {}
    try:
        while True:
            for agent in ("orchestrator", "dark-web-agent", "threat-intel-agent"):
                stream = f"unishield:agent:{agent}:findings"
                lid = last_ids.get(stream, "0")
                entries = await read_stream(stream, lid, count=5, block_ms=1000)
                for msg_id, data in entries:
                    last_ids[stream] = msg_id
                    if data.get("tenant_id") == client_id:
                        await websocket.send_json({"agent": agent, "finding": data})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
