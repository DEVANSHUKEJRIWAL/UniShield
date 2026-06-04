"""Live OpenClaw Gateway WebSocket client."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

import websockets

logger = logging.getLogger(__name__)

DEFAULT_CLIENT = {
    "name": "UniShield Orchestrator",
    "version": "2.0.0",
    "platform": "linux",
    "mode": "control",
}


def normalize_gateway_url(url: str) -> str:
    """Normalize gateway URL to OpenClaw root WebSocket endpoint."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("ws", "wss"):
        raise ValueError(f"Invalid OpenClaw gateway URL: {url}")
    path = parsed.path.rstrip("/")
    if path.endswith("/gateway"):
        path = path[: -len("/gateway")]
    if not path:
        path = "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def map_agent_id(agent_id: str) -> str:
    """Map UniShield agent IDs to OpenClaw agentId values."""
    return agent_id.removeprefix("unishield-")


class OpenClawGatewayError(Exception):
    """Raised when the OpenClaw gateway returns an error."""


class OpenClawGateway:
    """Async JSON-RPC client for the OpenClaw Gateway WebSocket API."""

    def __init__(
        self,
        ws_url: str,
        api_key: str = "",
        *,
        timeout_seconds: float = 300.0,
    ) -> None:
        self.ws_url = normalize_gateway_url(ws_url)
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self._ws: Any = None
        self._reader_task: asyncio.Task | None = None
        self._request_id = 0
        self._pending: dict[int | str, asyncio.Future] = {}
        self._run_text: dict[str, list[str]] = {}
        self._run_done: dict[str, asyncio.Event] = {}
        self._connected = asyncio.Event()

    async def connect(self) -> None:
        if self._ws is not None:
            return
        logger.info("Connecting to OpenClaw gateway at %s", self.ws_url)
        self._ws = await websockets.connect(
            self.ws_url,
            max_size=16 * 1024 * 1024,
            open_timeout=30,
        )
        self._reader_task = asyncio.create_task(self._read_loop())
        await self._rpc(
            "connect",
            {
                "role": "control",
                "auth": {"token": self.api_key} if self.api_key else {},
                "client": DEFAULT_CLIENT,
            },
        )
        self._connected.set()
        logger.info("OpenClaw gateway connected")

    async def close(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        self._connected.clear()

    async def invoke_agent(
        self,
        agent_id: str,
        message: str,
        session_name: str,
        *,
        timeout_seconds: float | None = None,
    ) -> tuple[str, int]:
        """Invoke an agent and wait for completion. Returns (content, latency_ms)."""
        await self._connected.wait()
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        started = time.monotonic()
        self._run_text[run_id] = []
        self._run_done[run_id] = asyncio.Event()

        await self._rpc(
            "agent",
            {
                "message": message,
                "sessionKey": session_name,
                "runId": run_id,
                "agentId": map_agent_id(agent_id),
                "deliver": False,
            },
        )

        wait_timeout = timeout_seconds or self.timeout_seconds
        try:
            await self._rpc(
                "agent.wait",
                {"runId": run_id, "timeoutSeconds": int(wait_timeout)},
                timeout=wait_timeout + 5,
            )
        except TimeoutError:
            logger.warning("agent.wait timed out for run %s — using streamed text", run_id)

        await asyncio.wait_for(self._run_done[run_id].wait(), timeout=5)
        latency_ms = int((time.monotonic() - started) * 1000)
        content = "".join(self._run_text.pop(run_id, []))
        self._run_done.pop(run_id, None)

        if not content:
            content = json.dumps({"status": "ok", "agent": agent_id, "runId": run_id})

        return content, latency_ms

    async def _rpc(
        self,
        method: str,
        params: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        if self._ws is None:
            raise OpenClawGatewayError("Gateway is not connected")
        self._request_id += 1
        request_id = self._request_id
        frame = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._pending[request_id] = future
        await self._ws.send(json.dumps(frame))
        try:
            response = await asyncio.wait_for(future, timeout=timeout or self.timeout_seconds)
        except asyncio.TimeoutError as exc:
            self._pending.pop(request_id, None)
            raise TimeoutError(f"OpenClaw RPC {method} timed out") from exc
        if not response.get("ok", True):
            error = response.get("error") or {}
            message = error.get("message") or str(error) or f"{method} failed"
            raise OpenClawGatewayError(message)
        payload = response.get("payload") or {}
        return payload if isinstance(payload, dict) else {"result": payload}

    async def _read_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                try:
                    frame = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("Ignoring non-JSON gateway frame")
                    continue
                await self._handle_frame(frame)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("OpenClaw gateway read loop failed")
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(OpenClawGatewayError("Gateway connection lost"))
            self._pending.clear()

    async def _handle_frame(self, frame: dict[str, Any]) -> None:
        if frame.get("event"):
            await self._handle_event(frame)
            return

        request_id = frame.get("id")
        if request_id in self._pending:
            future = self._pending.pop(request_id)
            if not future.done():
                future.set_result(frame)

    async def _handle_event(self, frame: dict[str, Any]) -> None:
        event = frame.get("event")
        payload = frame.get("payload") or {}
        if event != "agent":
            return

        run_id = payload.get("runId")
        if not run_id:
            return

        stream = payload.get("stream")
        data = payload.get("data") or {}

        if stream == "assistant":
            text = data.get("text") or ""
            if text:
                self._run_text.setdefault(run_id, []).append(text)
        elif stream == "lifecycle" and data.get("phase") in ("end", "error"):
            done = self._run_done.get(run_id)
            if done:
                done.set()
