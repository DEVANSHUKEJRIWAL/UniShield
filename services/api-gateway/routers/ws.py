"""WebSocket real-time event streaming."""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from packages.core.redis_client import read_stream
from packages.shared_types.constants import AgentName, RedisStream

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
    """Live agent output stream for all 13 registered agents."""
    await websocket.accept()
    await websocket.send_json({"status": "connected", "client_id": client_id, "agents": len(AgentName)})
    last_ids: dict[str, str] = {}
    agent_names = [a.value for a in AgentName]
    try:
        while True:
            for agent in agent_names:
                stream = RedisStream.agent_findings(agent)
                lid = last_ids.get(stream, "0")
                try:
                    entries = await read_stream(stream, lid, count=5, block_ms=500)
                except Exception:
                    continue
                for msg_id, data in entries:
                    last_ids[stream] = msg_id
                    if data.get("tenant_id") == client_id:
                        await websocket.send_json({"agent": agent, "finding": data})
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
