"""Search API — Elasticsearch with DB fallback (Week 5)."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import Finding
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission
from services.search.service import search_service

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("/{client_id}")
async def search_findings(
    client_id: str,
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
    user: CurrentUser = Depends(require_permission("read:findings")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Full-text search findings for tenant."""
    enforce_tenant(user, client_id)
    es_hits = await search_service.search(client_id, q, limit=limit)
    if es_hits:
        return {"source": "elasticsearch", "query": q, "results": es_hits}

    pattern = f"%{q}%"
    result = await db.execute(
        select(Finding)
        .where(
            Finding.tenant_id == client_id,
            or_(Finding.title.ilike(pattern), Finding.description.ilike(pattern)),
        )
        .order_by(Finding.created_at.desc())
        .limit(limit)
    )
    db_hits = [
        {
            "tenant_id": f.tenant_id,
            "agent_id": f.agent_id,
            "severity": f.severity,
            "title": f.title,
            "description": f.description[:300],
            "confidence": f.confidence,
        }
        for f in result.scalars().all()
    ]
    return {"source": "database", "query": q, "results": db_hits}
