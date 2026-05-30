"""ThreatIntelAgent implementation."""

from typing import Any

from agents._openclaw.base import OpenClawAgent


class ThreatIntelAgent(OpenClawAgent):
    """Query external threat intelligence sources."""

    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name="threat-intel-agent",
            tenant_id=tenant_id,
            **kwargs,
        )

    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return system prompt with KG context."""
        return (
            f"You are the UniShield threat intel agent agent. "
            f"Tenant: {self.tenant_id}. Context: {kg_context}"
        )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Return Anthropic tool schemas."""
        return []

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute a tool call."""
        return {"error": f"Tool {tool_name} not yet implemented"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle incoming normalised event."""
        await self.reason(str(event), kg_context={"event": event})
