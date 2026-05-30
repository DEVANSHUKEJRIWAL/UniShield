"""servicenow connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class ServicenowConnector(BaseConnector):
    """Integration adapter for servicenow."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from servicenow."""
        return [
            {
                "source_vendor": "servicenow",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from servicenow",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "servicenow", "action": action}
