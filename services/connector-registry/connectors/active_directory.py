"""active_directory connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class ActiveDirectoryConnector(BaseConnector):
    """Integration adapter for active_directory."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from active_directory."""
        return [
            {
                "source_vendor": "active_directory",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from active_directory",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "active_directory", "action": action}
