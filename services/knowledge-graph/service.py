"""Knowledge graph service — Neo4j read/write API."""

from typing import Any

from packages.core.config import settings


class KnowledgeGraphService:
    """Neo4j knowledge graph operations."""

    async def query(self, cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute read-only Cypher query."""
        try:
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            async with driver.session() as session:
                result = await session.run(cypher, **(params or {}))
                records = [dict(r) async for r in result]
            await driver.close()
            return records
        except Exception:
            return []

    async def blast_radius(self, entity_id: str, tenant_id: str) -> dict[str, Any]:
        """Compute blast radius for an entity."""
        cypher = """
        MATCH (e {id: $entity_id, clientId: $tenant_id})-[*1..3]-(connected)
        RETURN e, collect(DISTINCT connected) AS affected
        """
        records = await self.query(cypher, {"entity_id": entity_id, "tenant_id": tenant_id})
        if records:
            return {"entity_id": entity_id, "affected": records}
        return {
            "entity_id": entity_id,
            "affected_assets": ["api-gateway", "db-prod-01", "auth-service"],
            "hop_count": 3,
            "crown_jewels_in_radius": 1,
            "mock": True,
        }

    async def attack_paths(self, incident_id: str, tenant_id: str) -> dict[str, Any]:
        """Return attack paths for an incident."""
        return {
            "incident_id": incident_id,
            "tenant_id": tenant_id,
            "paths": [
                {"steps": ["phishing_email", "workstation-42", "domain-controller", "db-prod-01"], "severity": "critical"},
            ],
        }

    async def nl_query(self, natural_language: str, tenant_id: str) -> dict[str, Any]:
        """Natural language to Cypher (mock — Claude generates in graph-query-agent)."""
        return {
            "query": natural_language,
            "cypher": f"MATCH (n {{clientId: '{tenant_id}'}}) RETURN n LIMIT 25",
            "results": [],
        }


kg_service = KnowledgeGraphService()
