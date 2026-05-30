"""virustotal connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class VirustotalConnector(BaseConnector):
    """Integration adapter for virustotal."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from virustotal."""
        return [
            {
                "source_vendor": "virustotal",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from virustotal",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "virustotal", "action": action}
