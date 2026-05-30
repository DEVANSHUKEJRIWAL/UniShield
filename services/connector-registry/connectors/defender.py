"""defender connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class DefenderConnector(BaseConnector):
    """Integration adapter for defender."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from defender."""
        return [
            {
                "source_vendor": "defender",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from defender",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "defender", "action": action}
