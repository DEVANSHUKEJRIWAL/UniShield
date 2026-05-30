"""metricstream connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class MetricstreamConnector(BaseConnector):
    """Integration adapter for metricstream."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from metricstream."""
        return [
            {
                "source_vendor": "metricstream",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from metricstream",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "metricstream", "action": action}
