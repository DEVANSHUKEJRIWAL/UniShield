"""OpenClaw Gateway client — delegates to the openclaw CLI inside Docker."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Optional

logger = logging.getLogger(__name__)


def normalize_gateway_url(url: str) -> str:
    return url


def map_agent_id(agent_id: str) -> str:
    return agent_id.removeprefix("unishield-")


class OpenClawGatewayError(Exception):
    pass


class OpenClawGateway:
    """Invokes OpenClaw agents via the CLI inside the Docker container."""

    def __init__(
        self,
        ws_url: str,
        api_key: str = "",
        *,
        timeout_seconds: float = 300.0,
    ) -> None:
        self.ws_url = ws_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self._container = "unishield-openclaw-1"

    async def connect(self) -> None:
        if self._ws is not None:
            return
        logger.info("Connecting to OpenClaw gateway at %s", self.ws_url)
        try:
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
        except Exception:
            await self.close()
            raise
        self._connected.set()
        logger.info("OpenClaw gateway connected")

    async def _ensure_connected(self) -> None:
        if self._ws is None:
            self._connected.clear()
            await self.connect()

    async def close(self) -> None:
        pass

    async def invoke_agent(
        self,
        agent_id: str,
        message: str,
        session_name: str,
        *,
        timeout_seconds: float | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, int]:
        """Invoke an agent and wait for completion. Returns (content, latency_ms)."""
        await self._ensure_connected()
        await self._connected.wait()
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        started = time.monotonic()
        timeout = timeout_seconds or self.timeout_seconds

        cmd = [
            "docker", "exec", self._container,
            "node", "dist/index.js", "agent",
            "--agent", mapped_id,
            "--session-key", f"agent:{mapped_id}:{session_name}",
            "--message", message,
            "--json",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            proc.kill()
            raise OpenClawGatewayError(f"Agent {agent_id} timed out after {timeout}s") from exc

        latency_ms = int((time.monotonic() - started) * 1000)

        if proc.returncode != 0:
            err = stderr.decode()[:500]
            raise OpenClawGatewayError(f"Agent {agent_id} failed: {err}")

        output = stdout.decode().strip()
        if not output:
            raise OpenClawGatewayError(f"Agent {agent_id} returned empty output")

    async def _rpc(
        self,
        method: str,
        params: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        await self._ensure_connected()
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
        except Exception as exc:
            logger.exception("OpenClaw gateway read loop failed")
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(
                        OpenClawGatewayError(f"Gateway connection lost: {exc}")
                    )
            self._pending.clear()
            self._ws = None
            self._connected.clear()

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
