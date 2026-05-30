"""misp connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class MispConnector(BaseConnector):
    """Integration adapter for misp."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from misp."""
        return [
            {
                "source_vendor": "misp",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from misp",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "misp", "action": action}
