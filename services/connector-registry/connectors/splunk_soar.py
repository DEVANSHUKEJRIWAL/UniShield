"""splunk_soar connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class SplunkSoarConnector(BaseConnector):
    """Integration adapter for splunk_soar."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from splunk_soar."""
        return [
            {
                "source_vendor": "splunk_soar",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from splunk_soar",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "splunk_soar", "action": action}
