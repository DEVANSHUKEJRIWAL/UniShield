"""guardduty connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class GuarddutyConnector(BaseConnector):
    """Integration adapter for guardduty."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from guardduty."""
        return [
            {
                "source_vendor": "guardduty",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from guardduty",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "guardduty", "action": action}
