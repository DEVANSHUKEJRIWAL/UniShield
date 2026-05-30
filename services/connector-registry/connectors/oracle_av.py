"""oracle_av connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class OracleAvConnector(BaseConnector):
    """Integration adapter for oracle_av."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from oracle_av."""
        return [
            {
                "source_vendor": "oracle_av",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from oracle_av",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "oracle_av", "action": action}
