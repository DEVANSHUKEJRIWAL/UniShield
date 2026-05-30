"""taxii_client connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class TaxiiClientConnector(BaseConnector):
    """Integration adapter for taxii_client."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from taxii_client."""
        return [
            {
                "source_vendor": "taxii_client",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from taxii_client",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "taxii_client", "action": action}
