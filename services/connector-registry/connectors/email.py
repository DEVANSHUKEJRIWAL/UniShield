"""email connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class EmailConnector(BaseConnector):
    """Integration adapter for email."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from email."""
        return [
            {
                "source_vendor": "email",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from email",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "email", "action": action}
