"""shodan connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class ShodanConnector(BaseConnector):
    """Integration adapter for shodan."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from shodan."""
        return [
            {
                "source_vendor": "shodan",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from shodan",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "shodan", "action": action}
