"""qradar connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class QradarConnector(BaseConnector):
    """Integration adapter for qradar."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from qradar."""
        return [
            {
                "source_vendor": "qradar",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from qradar",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "qradar", "action": action}
