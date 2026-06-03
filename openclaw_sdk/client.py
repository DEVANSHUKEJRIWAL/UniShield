"""OpenClaw gateway client."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.types import ExecutionResult

logger = logging.getLogger(__name__)

# Global mock handler: agent_id -> async callable(prompt) -> str
MOCK_RESPONSE_HANDLERS: dict[str, callable] = {}


class OpenClawAgent:
    """Handle to a single OpenClaw agent session."""

    def __init__(
        self,
        client: "OpenClawClient",
        agent_id: str,
        session_name: Optional[str] = None,
    ) -> None:
        self._client = client
        self.agent_id = agent_id
        self.session_name = session_name or "default"

    async def execute(self, query: str) -> ExecutionResult:
        if self._client.config.mock_mode:
            handler = MOCK_RESPONSE_HANDLERS.get(self.agent_id)
            if handler:
                content = await handler(query)
            else:
                content = json.dumps({"status": "ok", "agent": self.agent_id})
            return ExecutionResult(success=True, content=content, latency_ms=1)

        raise NotImplementedError(
            "Live OpenClaw gateway connection not configured. "
            "Set OPENCLAW_MOCK_MODE=true for local development."
        )


class OpenClawClient:
    """Client connecting to the OpenClaw WebSocket gateway."""

    def __init__(self, config: ClientConfig, callbacks: Optional[list] = None) -> None:
        self.config = config
        self.callbacks = callbacks or []

    @classmethod
    @asynccontextmanager
    async def connect(
        cls,
        gateway_ws_url: str = "ws://127.0.0.1:18789/gateway",
        api_key: str = "",
        mock_mode: bool = False,
        callbacks: Optional[list] = None,
        **kwargs,
    ) -> AsyncIterator["OpenClawClient"]:
        config = ClientConfig(
            gateway_ws_url=gateway_ws_url,
            api_key=api_key,
            mock_mode=mock_mode or kwargs.get("mock_mode", False),
        )
        client = cls(config, callbacks=callbacks)
        yield client

    def get_agent(
        self,
        agent_id: str,
        session_name: Optional[str] = None,
    ) -> OpenClawAgent:
        return OpenClawAgent(self, agent_id, session_name=session_name)
