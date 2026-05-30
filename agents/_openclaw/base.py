"""OpenClaw agent runtime — base class for all UniShield agents."""

from abc import ABC, abstractmethod
from typing import Any

import asyncio

from anthropic import Anthropic

from packages.shared_types.constants import RedisStream


class OpenClawAgent(ABC):
    """
    Base class for all UniShield agents.
    Implements the persistent, event-driven agent loop.
    Agents run as daemon processes — no user prompt required.
    LangGraph handles multi-agent routing above this level.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        tenant_id: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        heartbeat_interval_seconds: int = 60,
    ) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.tenant_id = tenant_id
        self.client = Anthropic()  # API key from environment
        self.model = model
        self.max_tokens = max_tokens
        self.heartbeat_interval = heartbeat_interval_seconds
        self.memory: list[dict[str, Any]] = []  # Rolling 20-turn in-context memory
        self.running = False

    @abstractmethod
    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return system prompt injected with KG context slice for this tenant."""
        ...

    @abstractmethod
    async def get_tools(self) -> list[dict[str, Any]]:
        """Return Anthropic tool schemas for this agent's toolset."""
        ...

    @abstractmethod
    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute a tool call and return the result."""
        ...

    @abstractmethod
    async def on_event(self, event: dict[str, Any]) -> None:
        """Called when a new normalised event arrives from Redis Streams."""
        ...

    async def reason(self, user_turn: str, kg_context: dict[str, Any]) -> str:
        """
        Core reasoning loop. Calls Claude with full context + tools.
        Handles multi-turn tool use. Emits findings to Redis on completion.
        """
        messages: list[dict[str, Any]] = self.memory + [{"role": "user", "content": user_turn}]
        tools = await self.get_tools()
        system = self.get_system_prompt(kg_context)

        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                tools=tools,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                text = next(
                    (block.text for block in response.content if hasattr(block, "text")),
                    "",
                )
                await self.emit_finding(text)
                self.memory = messages[-20:]  # Retain last 20 turns
                return text

            if response.stop_reason == "tool_use":
                tool_results: list[dict[str, Any]] = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self.handle_tool_call(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": str(result),
                            }
                        )
                messages.append({"role": "user", "content": tool_results})

        raise RuntimeError("Unexpected exit from reasoning loop")

    async def emit_finding(self, finding_text: str) -> None:
        """Push structured finding to Redis Streams unishield:agent:<name>:findings."""
        stream_key = RedisStream.agent_findings(self.agent_name)
        # Redis producer wired in Week 2 — stub for Week 1 foundation
        _ = stream_key, finding_text

    async def emit_hitl_request(self, action: dict[str, Any], confidence: float, reasoning: str) -> None:
        """
        Emit to HITL queue when proposed action needs human approval.
        HITL policy — see §11.
        """
        _ = action, confidence, reasoning, RedisStream.HITL_QUEUE

    async def run(self) -> None:
        """Daemon loop: consume Redis Streams + heartbeat scheduler."""
        self.running = True
        await asyncio.gather(
            self._redis_consumer_loop(),
            self._heartbeat_loop(),
        )

    async def _redis_consumer_loop(self) -> None:
        """Consume events from agent task stream."""
        while self.running:
            await asyncio.sleep(1)

    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat for agent health monitoring."""
        while self.running:
            await asyncio.sleep(self.heartbeat_interval)
