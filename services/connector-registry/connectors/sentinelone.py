"""sentinelone connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class SentineloneConnector(BaseConnector):
    """Integration adapter for sentinelone."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from sentinelone."""
        return [
            {
                "source_vendor": "sentinelone",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from sentinelone",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "sentinelone", "action": action}
