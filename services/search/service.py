"""Elasticsearch indexing for findings (Week 5)."""

from typing import Any

import httpx

from packages.core.config import settings


class SearchService:
    """Index and search security findings."""

    INDEX = "unishield-findings"

    async def index_finding(self, finding: dict[str, Any]) -> bool:
        """Index finding document (mock when ES unavailable)."""
        doc_id = finding.get("id") or finding.get("finding_id")
        if not doc_id:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.put(
                    f"{settings.elasticsearch_url}/{self.INDEX}/_doc/{doc_id}",
                    json={
                        "tenant_id": finding.get("tenant_id"),
                        "agent_id": finding.get("agent_id"),
                        "severity": finding.get("severity"),
                        "title": finding.get("title"),
                        "description": finding.get("description"),
                        "confidence": finding.get("confidence"),
                    },
                )
                return resp.status_code in (200, 201)
        except Exception:
            return False

    async def search(self, tenant_id: str, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Full-text search findings for tenant."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{settings.elasticsearch_url}/{self.INDEX}/_search",
                    json={
                        "size": limit,
                        "query": {
                            "bool": {
                                "must": [
                                    {"match": {"title": query}},
                                    {"term": {"tenant_id": tenant_id}},
                                ]
                            }
                        },
                    },
                )
                if resp.status_code == 200:
                    hits = resp.json().get("hits", {}).get("hits", [])
                    return [h.get("_source", {}) for h in hits]
        except Exception:
            pass
        return []


search_service = SearchService()
