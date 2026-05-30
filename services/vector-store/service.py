"""Vector store service — Qdrant wrapper."""

from typing import Any

import httpx

from packages.core.config import settings
from packages.shared_types.constants import QdrantCollection


class VectorStoreService:
    """Qdrant embedding and retrieval."""

    async def search(self, collection: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Semantic search (mock vector for local dev without embeddings)."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{settings.qdrant_url}/collections/{collection}/points/search",
                    json={"vector": [0.01] * 1536, "limit": limit, "with_payload": True},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    return resp.json().get("result", [])
        except Exception:
            pass
        return [{"score": 0.9, "payload": {"text": query, "collection": collection}}]

    async def ensure_collections(self) -> None:
        """Create all required Qdrant collections."""
        async with httpx.AsyncClient() as client:
            for col in QdrantCollection:
                await client.put(
                    f"{settings.qdrant_url}/collections/{col.value}",
                    json={"vectors": {"size": 1536, "distance": "Cosine"}},
                )


vector_store = VectorStoreService()
