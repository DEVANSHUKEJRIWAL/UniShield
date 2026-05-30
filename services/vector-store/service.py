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

    async def embed_corpus(self, collection: str, documents: list[dict[str, str]]) -> dict[str, Any]:
        """Embed text documents into Qdrant (mock vectors for local dev)."""
        await self.ensure_collections()
        points = []
        for i, doc in enumerate(documents):
            text = doc.get("text", "")
            points.append(
                {
                    "id": i + 1,
                    "vector": [0.01 * ((i + j) % 10) for j in range(1536)],
                    "payload": {"text": text, **{k: v for k, v in doc.items() if k != "text"}},
                }
            )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.put(
                    f"{settings.qdrant_url}/collections/{collection}/points",
                    json={"points": points},
                )
                if resp.status_code in (200, 201):
                    return {"collection": collection, "embedded": len(points), "status": "ok"}
        except Exception as exc:
            return {"collection": collection, "embedded": len(points), "status": "mock", "error": str(exc)}
        return {"collection": collection, "embedded": len(points), "status": "mock"}


vector_store = VectorStoreService()
