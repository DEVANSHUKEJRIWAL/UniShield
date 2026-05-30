"""pgaudit connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class PgauditConnector(BaseConnector):
    """Integration adapter for pgaudit."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from pgaudit."""
        return [
            {
                "source_vendor": "pgaudit",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from pgaudit",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "pgaudit", "action": action}
