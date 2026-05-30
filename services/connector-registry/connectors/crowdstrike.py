"""crowdstrike connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class CrowdstrikeConnector(BaseConnector):
    """Integration adapter for crowdstrike."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from crowdstrike."""
        return [
            {
                "source_vendor": "crowdstrike",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from crowdstrike",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "crowdstrike", "action": action}
