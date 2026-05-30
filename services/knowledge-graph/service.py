"""Knowledge graph service — Neo4j read/write API."""

from typing import Any

from packages.core.config import settings


class KnowledgeGraphService:
    """Neo4j knowledge graph operations."""

    async def _driver(self):
        from neo4j import AsyncGraphDatabase

        return AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    async def query(self, cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute read-only Cypher query."""
        try:
            driver = await self._driver()
            async with driver.session() as session:
                result = await session.run(cypher, **(params or {}))
                records = [dict(r) async for r in result]
            await driver.close()
            return records
        except Exception:
            return []

    async def write(self, cypher: str, params: dict[str, Any] | None = None) -> bool:
        """Execute write Cypher."""
        try:
            driver = await self._driver()
            async with driver.session() as session:
                await session.run(cypher, **(params or {}))
            await driver.close()
            return True
        except Exception:
            return False

    async def write_finding(self, finding: dict[str, Any]) -> None:
        """Upsert Finding node linked to Client tenant."""
        tenant_id = finding.get("tenant_id", "")
        finding_id = str(finding.get("finding_id", finding.get("id", "")))
        if not tenant_id or not finding_id:
            return
        cypher = """
        MERGE (c:Client {id: $tenant_id})
        ON CREATE SET c.name = $tenant_id
        MERGE (f:Finding {id: $finding_id, clientId: $tenant_id})
        SET f.title = $title,
            f.severity = $severity,
            f.agentId = $agent_id,
            f.type = $type,
            f.confidence = $confidence,
            f.updatedAt = datetime()
        MERGE (c)-[:HAS_FINDING]->(f)
        WITH f
        UNWIND $evidence AS ev
        MERGE (a:Asset {id: ev, clientId: $tenant_id})
        MERGE (f)-[:AFFECTS]->(a)
        """
        evidence = finding.get("evidence_references", [])[:5]
        if not evidence:
            evidence = [finding.get("agent_id", "unknown-asset")]
        await self.write(
            cypher,
            {
                "tenant_id": tenant_id,
                "finding_id": finding_id,
                "title": (finding.get("title") or "Finding")[:512],
                "severity": finding.get("severity", "medium"),
                "agent_id": finding.get("agent_id", "unknown"),
                "type": finding.get("type", "analysis"),
                "confidence": float(finding.get("confidence", 0.0)),
                "evidence": evidence,
            },
        )

    async def upsert_agent_run(self, agent_name: str, tenant_id: str, status: str) -> None:
        """Record agent execution node."""
        cypher = """
        MERGE (c:Client {id: $tenant_id})
        MERGE (a:Agent {name: $agent_name, clientId: $tenant_id})
        SET a.lastStatus = $status, a.lastRunAt = datetime()
        MERGE (c)-[:RUNS_AGENT]->(a)
        """
        await self.write(cypher, {"tenant_id": tenant_id, "agent_name": agent_name, "status": status})

    async def blast_radius(self, entity_id: str, tenant_id: str) -> dict[str, Any]:
        """Compute blast radius for an entity."""
        cypher = """
        MATCH (e {id: $entity_id, clientId: $tenant_id})-[*1..3]-(connected)
        RETURN e.id AS source, collect(DISTINCT connected.id) AS affected
        """
        records = await self.query(cypher, {"entity_id": entity_id, "tenant_id": tenant_id})
        if records:
            affected = records[0].get("affected", [])
            return {
                "entity_id": entity_id,
                "affected_assets": affected,
                "hop_count": 3,
                "crown_jewels_in_radius": sum(1 for a in affected if "db" in str(a).lower()),
                "mock": False,
            }
        return {
            "entity_id": entity_id,
            "affected_assets": ["api-gateway", "db-prod-01", "auth-service"],
            "hop_count": 3,
            "crown_jewels_in_radius": 1,
            "mock": True,
        }

    async def attack_paths(self, incident_id: str, tenant_id: str) -> dict[str, Any]:
        """Return attack paths via variable-length graph traversal."""
        cypher = """
        MATCH path = (f:Finding {clientId: $tenant_id})-[*1..4]->(target:Asset)
        WHERE f.id = $incident_id OR $incident_id IN [n IN nodes(path) | n.id]
        RETURN [n IN nodes(path) | coalesce(n.id, n.title, labels(n)[0])] AS steps
        LIMIT 5
        """
        records = await self.query(cypher, {"incident_id": incident_id, "tenant_id": tenant_id})
        if records:
            paths = [{"steps": r.get("steps", []), "severity": "high"} for r in records]
            return {"incident_id": incident_id, "tenant_id": tenant_id, "paths": paths, "mock": False}
        return {
            "incident_id": incident_id,
            "tenant_id": tenant_id,
            "paths": [
                {"steps": ["phishing_email", "workstation-42", "domain-controller", "db-prod-01"], "severity": "critical"},
            ],
            "mock": True,
        }

    async def traverse_paths(self, source_entity: str, tenant_id: str, depth: int = 5) -> dict[str, Any]:
        """Multi-hop attack path from source entity."""
        cypher = f"""
        MATCH path = (src {{id: $source, clientId: $tenant_id}})-[*1..{min(depth, 6)}]->(dst)
        WHERE dst:Asset OR dst:Service
        RETURN [n IN nodes(path) | coalesce(n.id, n.title)] AS hops,
               coalesce(dst.criticality, '') = 'high' AS crown_jewel_reached
        LIMIT 10
        """
        records = await self.query(
            cypher,
            {"source": source_entity, "tenant_id": tenant_id, "depth": min(depth, 6)},
        )
        if records:
            return {
                "source": source_entity,
                "depth": depth,
                "paths": [
                    {"hops": r.get("hops", []), "crown_jewel_reached": bool(r.get("crown_jewel_reached"))}
                    for r in records
                ],
                "mock": False,
            }
        return {
            "source": source_entity,
            "depth": depth,
            "paths": [{"hops": [source_entity, "internal-api", "db-prod-01"], "crown_jewel_reached": True}],
            "mock": True,
        }

    async def nl_query(self, natural_language: str, tenant_id: str) -> dict[str, Any]:
        """Natural language to Cypher — tenant-scoped read query."""
        cypher = "MATCH (n {clientId: $tenant_id}) RETURN n LIMIT 25"
        if "finding" in natural_language.lower():
            cypher = "MATCH (f:Finding {clientId: $tenant_id}) RETURN f ORDER BY f.updatedAt DESC LIMIT 25"
        elif "asset" in natural_language.lower():
            cypher = "MATCH (a:Asset {clientId: $tenant_id}) RETURN a LIMIT 25"
        results = await self.query(cypher, {"tenant_id": tenant_id})
        return {"query": natural_language, "cypher": cypher, "results": results}


kg_service = KnowledgeGraphService()
