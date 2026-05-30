"""splunk connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class SplunkConnector(BaseConnector):
    """Integration adapter for splunk."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from splunk."""
        return [
            {
                "source_vendor": "splunk",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from splunk",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "splunk", "action": action}
