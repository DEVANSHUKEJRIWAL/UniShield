"""OpenClaw gateway client."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.types import ExecutionResult
from openclaw_sdk.gateway import OpenClawGateway, OpenClawGatewayError

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

    async def execute(
        self,
        query: str,
        *,
        system_prompt: str | None = None,
    ) -> ExecutionResult:
        callbacks = self._client.callbacks
        for callback in callbacks:
            await callback.on_execution_start(self.agent_id, query)

        try:
            if self._client.config.mock_mode:
                handler = MOCK_RESPONSE_HANDLERS.get(self.agent_id)
                if handler:
                    content = await handler(query)
                else:
                    raise OpenClawGatewayError(
                        f"No mock handler registered for agent {self.agent_id}. "
                        "Register one in tests or disable OPENCLAW_MOCK_MODE."
                    )
                result = ExecutionResult(success=True, content=content, latency_ms=1)
            else:
                gateway = self._client._gateway
                if gateway is None:
                    raise OpenClawGatewayError(
                        "Live OpenClaw gateway is not connected. "
                        "Start the gateway with OPENCLAW_MOCK_MODE=false."
                    )
                content, latency_ms = await gateway.invoke_agent(
                    self.agent_id,
                    query,
                    self.session_name,
                    system_prompt=system_prompt,
                )
                result = ExecutionResult(
                    success=True,
                    content=content,
                    latency_ms=latency_ms,
                    metadata={"mode": "live"},
                )

            for callback in callbacks:
                await callback.on_execution_end(self.agent_id, result)
            return result
        except Exception as exc:
            for callback in callbacks:
                await callback.on_execution_error(self.agent_id, exc)
            raise


class OpenClawClient:
    """Client connecting to the OpenClaw WebSocket gateway."""

    def __init__(self, config: ClientConfig, callbacks: Optional[list] = None) -> None:
        self.config = config
        self.callbacks = callbacks or []
        self._gateway: OpenClawGateway | None = None

    @classmethod
    @asynccontextmanager
    async def connect(
        cls,
        gateway_ws_url: str = "ws://127.0.0.1:18789/",
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
        if not config.mock_mode:
            gateway = OpenClawGateway(
                config.gateway_ws_url,
                config.api_key,
            )
            await gateway.connect()
            client._gateway = gateway
        try:
            yield client
        finally:
            if client._gateway is not None:
                await client._gateway.close()
                client._gateway = None

    def get_agent(
        self,
        agent_id: str,
        session_name: Optional[str] = None,
    ) -> OpenClawAgent:
        return OpenClawAgent(self, agent_id, session_name=session_name)
