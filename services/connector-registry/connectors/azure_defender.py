"""azure_defender connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class AzureDefenderConnector(BaseConnector):
    """Integration adapter for azure_defender."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from azure_defender."""
        return [
            {
                "source_vendor": "azure_defender",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from azure_defender",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "azure_defender", "action": action}
