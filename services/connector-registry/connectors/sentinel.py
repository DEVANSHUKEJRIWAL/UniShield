"""sentinel connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class SentinelConnector(BaseConnector):
    """Integration adapter for sentinel."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from sentinel."""
        return [
            {
                "source_vendor": "sentinel",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from sentinel",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "sentinel", "action": action}
