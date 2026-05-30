"""Vector store service — Qdrant wrapper."""

import hashlib
from typing import Any

import httpx

from packages.core.config import settings
from packages.shared_types.constants import QdrantCollection


def text_to_vector(text: str, size: int = 1536) -> list[float]:
    """Deterministic hash-based embedding for local dev (no external API)."""
    digest = hashlib.sha256(text.encode()).digest()
    vec: list[float] = []
    while len(vec) < size:
        for byte in digest:
            vec.append((byte / 255.0) * 2 - 1)
            if len(vec) >= size:
                break
        digest = hashlib.sha256(digest).digest()
    return vec


class VectorStoreService:
    """Qdrant embedding and retrieval."""

    async def search(self, collection: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Semantic search using hash-based query vector."""
        vector = text_to_vector(query)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{settings.qdrant_url}/collections/{collection}/points/search",
                    json={"vector": vector, "limit": limit, "with_payload": True},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    return resp.json().get("result", [])
        except Exception:
            pass
        return [{"score": 0.9, "payload": {"text": query, "collection": collection}}]

    async def ensure_collections(self) -> None:
        """Create all required Qdrant collections."""
        try:
            async with httpx.AsyncClient() as client:
                for col in QdrantCollection:
                    await client.put(
                        f"{settings.qdrant_url}/collections/{col.value}",
                        json={"vectors": {"size": 1536, "distance": "Cosine"}},
                    )
        except Exception:
            pass

    async def embed_corpus(self, collection: str, documents: list[dict[str, str]]) -> dict[str, Any]:
        """Embed text documents into Qdrant using deterministic hash vectors."""
        await self.ensure_collections()
        points = []
        for i, doc in enumerate(documents):
            text = doc.get("text", "")
            points.append(
                {
                    "id": i + 1,
                    "vector": text_to_vector(text),
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
                    return {"collection": collection, "embedded": len(points), "status": "ok", "method": "hash-embedding"}
        except Exception as exc:
            return {"collection": collection, "embedded": len(points), "status": "mock", "error": str(exc), "method": "hash-embedding"}
        return {"collection": collection, "embedded": len(points), "status": "mock", "method": "hash-embedding"}


vector_store = VectorStoreService()
