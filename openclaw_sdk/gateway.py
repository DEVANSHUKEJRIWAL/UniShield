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
        # Verify container is reachable
        proc = await asyncio.create_subprocess_exec(
            "docker", "exec", self._container,
            "node", "dist/index.js", "health",
            "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        if proc.returncode != 0:
            raise OpenClawGatewayError(f"OpenClaw gateway unreachable: {stderr.decode()[:200]}")
        logger.info("OpenClaw gateway reachable via CLI")

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
        mapped_id = "main"  # gateway only has "main" agent
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

        # Try to parse JSON response
        try:
            data = json.loads(output)
            content = (
                data.get("reply")
                or data.get("content")
                or data.get("text")
                or data.get("output")
                or output
            )
        except json.JSONDecodeError:
            content = output

        if not content:
            raise OpenClawGatewayError(f"Agent {agent_id} returned empty content")

        return str(content), latency_ms
