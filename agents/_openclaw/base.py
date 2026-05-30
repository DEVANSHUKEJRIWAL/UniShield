"""OpenClaw agent runtime — base class for all UniShield agents."""

import json
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

import asyncio

from anthropic import Anthropic, AuthenticationError

from packages.core.api_keys import anthropic_live_enabled
from packages.core.config import settings
from packages.core.redis_client import publish_finding, publish_hitl_request, read_stream
from packages.core.schemas import AgentFinding
from packages.shared_types.constants import RedisStream
from services.hitl_service.models import should_require_hitl


class OpenClawAgent(ABC):
    """
    Base class for all UniShield agents.
    Implements the persistent, event-driven agent loop.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        tenant_id: str,
        model: str | None = None,
        max_tokens: int = 4096,
        heartbeat_interval_seconds: int = 60,
    ) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.tenant_id = tenant_id
        self.client = Anthropic(api_key=settings.anthropic_api_key or None)
        self.model = model or settings.anthropic_model
        self.max_tokens = max_tokens
        self.heartbeat_interval = heartbeat_interval_seconds
        self.memory: list[dict[str, Any]] = []
        self.running = False
        self._last_stream_id = "0"

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
        """Core reasoning loop with multi-turn tool use."""
        if not anthropic_live_enabled():
            finding = AgentFinding(
                finding_id=str(uuid.uuid4()),
                tenant_id=self.tenant_id,
                agent_id=self.agent_name,
                type="analysis",
                severity="medium",
                confidence=0.75,
                title=f"{self.agent_name} analysis (mock mode)",
                description=f"Mock analysis for: {user_turn[:200]}",
                reasoning_summary=(
                    "Anthropic API key missing or invalid — returning mock finding for local dev."
                ),
                evidence_references=[],
                mitre_ttps_matched=[],
                contributing_agents=[self.agent_name],
            )
            await self.emit_structured_finding(finding)
            return finding.description

        messages: list[dict[str, Any]] = self.memory + [{"role": "user", "content": user_turn}]
        tools = await self.get_tools()
        system = self.get_system_prompt(kg_context)

        while True:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "system": system,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            try:
                response = self.client.messages.create(**kwargs)
            except AuthenticationError as exc:
                finding = AgentFinding(
                    finding_id=str(uuid.uuid4()),
                    tenant_id=self.tenant_id,
                    agent_id=self.agent_name,
                    type="analysis",
                    severity="medium",
                    confidence=0.75,
                    title=f"{self.agent_name} analysis (mock mode — auth failed)",
                    description=f"Mock analysis for: {user_turn[:200]}",
                    reasoning_summary=(
                        f"Anthropic rejected the API key ({exc}). "
                        "Verify ANTHROPIC_API_KEY in .env — using mock finding."
                    ),
                    evidence_references=[],
                    mitre_ttps_matched=[],
                    contributing_agents=[self.agent_name],
                )
                await self.emit_structured_finding(finding)
                return finding.description
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                text = next(
                    (block.text for block in response.content if hasattr(block, "text")),
                    "",
                )
                finding = AgentFinding(
                    finding_id=str(uuid.uuid4()),
                    tenant_id=self.tenant_id,
                    agent_id=self.agent_name,
                    type="analysis",
                    severity="medium",
                    confidence=0.85,
                    title=f"{self.agent_name} finding",
                    description=text[:2000],
                    reasoning_summary=text[:500],
                    contributing_agents=[self.agent_name],
                )
                await self.emit_structured_finding(finding)
                self.memory = messages[-20:]
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
                                "content": json.dumps(result) if isinstance(result, (dict, list)) else str(result),
                            }
                        )
                messages.append({"role": "user", "content": tool_results})

        raise RuntimeError("Unexpected exit from reasoning loop")

    async def emit_structured_finding(self, finding: AgentFinding) -> None:
        """Push validated finding to Redis, DB, and evaluate HITL."""
        data = finding.model_dump(mode="json")
        await publish_finding(self.agent_name, data)
        try:
            from packages.core.persistence import log_agent_run, persist_finding

            await persist_finding(finding)
            await log_agent_run(
                self.agent_name,
                self.tenant_id,
                status="completed",
                output=finding.description[:500],
            )
        except Exception:
            pass
        if finding.hitl_required or should_require_hitl(finding.confidence, "HIGH", finding.severity.upper()):
            await self.emit_hitl_request(
                {"finding_id": finding.finding_id, "actions": finding.recommended_actions},
                finding.confidence,
                finding.reasoning_summary,
            )

    async def emit_finding(self, finding_text: str) -> None:
        """Push text finding to Redis Streams."""
        await publish_finding(
            self.agent_name,
            {"text": finding_text, "tenant_id": self.tenant_id, "timestamp": datetime.now(UTC).isoformat()},
        )

    async def emit_hitl_request(self, action: dict[str, Any], confidence: float, reasoning: str) -> None:
        """Emit to HITL queue when human approval is required."""
        await publish_hitl_request(
            {
                "action_id": str(uuid.uuid4()),
                "tenant_id": self.tenant_id,
                "agent_id": self.agent_name,
                "action": action,
                "confidence": confidence,
                "reasoning": reasoning,
                "expiry_ts": datetime.now(UTC).isoformat(),
            }
        )

    async def run(self) -> None:
        """Daemon loop: consume Redis Streams + heartbeat."""
        self.running = True
        await asyncio.gather(self._redis_consumer_loop(), self._heartbeat_loop())

    async def _redis_consumer_loop(self) -> None:
        """Consume events from agent task stream."""
        stream = RedisStream.agent_tasks(self.agent_name)
        while self.running:
            try:
                entries = await read_stream(stream, self._last_stream_id, count=5, block_ms=5000)
                for msg_id, data in entries:
                    self._last_stream_id = msg_id
                    await self.on_event(data)
            except Exception:
                await asyncio.sleep(2)

    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat for agent health monitoring."""
        while self.running:
            await asyncio.sleep(self.heartbeat_interval)
