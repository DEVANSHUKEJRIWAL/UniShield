"""entra_id connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class EntraIdConnector(BaseConnector):
    """Integration adapter for entra_id."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from entra_id."""
        return [
            {
                "source_vendor": "entra_id",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from entra_id",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "entra_id", "action": action}
