"""pagerduty connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class PagerdutyConnector(BaseConnector):
    """Integration adapter for pagerduty."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from pagerduty."""
        return [
            {
                "source_vendor": "pagerduty",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from pagerduty",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "pagerduty", "action": action}
