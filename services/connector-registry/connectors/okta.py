"""okta connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class OktaConnector(BaseConnector):
    """Integration adapter for okta."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from okta."""
        return [
            {
                "source_vendor": "okta",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from okta",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "okta", "action": action}
