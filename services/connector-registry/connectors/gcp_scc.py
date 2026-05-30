"""gcp_scc connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class GcpSccConnector(BaseConnector):
    """Integration adapter for gcp_scc."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from gcp_scc."""
        return [
            {
                "source_vendor": "gcp_scc",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from gcp_scc",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "gcp_scc", "action": action}
