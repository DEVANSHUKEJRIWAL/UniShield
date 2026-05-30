"""Sync agent findings and assets to Neo4j knowledge graph (Week 7)."""

from typing import Any

from services.knowledge_graph.service import kg_service


async def sync_finding_to_kg(finding: dict[str, Any]) -> None:
    """Upsert Finding node and link to tenant Client after DB persist."""
    await kg_service.write_finding(finding)


async def sync_agent_run_to_kg(agent_name: str, tenant_id: str, status: str) -> None:
    """Record agent execution as a lightweight graph event."""
    await kg_service.upsert_agent_run(agent_name, tenant_id, status)
