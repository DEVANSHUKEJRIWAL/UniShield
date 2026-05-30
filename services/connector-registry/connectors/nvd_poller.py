"""nvd_poller connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class NvdPollerConnector(BaseConnector):
    """Integration adapter for nvd_poller."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from nvd_poller."""
        return [
            {
                "source_vendor": "nvd_poller",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from nvd_poller",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "nvd_poller", "action": action}
