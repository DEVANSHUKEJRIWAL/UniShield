"""sqlserver_audit connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class SqlserverAuditConnector(BaseConnector):
    """Integration adapter for sqlserver_audit."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from sqlserver_audit."""
        return [
            {
                "source_vendor": "sqlserver_audit",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from sqlserver_audit",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "sqlserver_audit", "action": action}
