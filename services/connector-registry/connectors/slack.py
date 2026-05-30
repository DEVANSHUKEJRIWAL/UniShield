"""slack connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class SlackConnector(BaseConnector):
    """Integration adapter for slack."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from slack."""
        return [
            {
                "source_vendor": "slack",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from slack",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "slack", "action": action}
