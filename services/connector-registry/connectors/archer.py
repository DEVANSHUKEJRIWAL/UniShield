"""archer connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class ArcherConnector(BaseConnector):
    """Integration adapter for archer."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from archer."""
        return [
            {
                "source_vendor": "archer",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from archer",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "archer", "action": action}
