"""Search API — Elasticsearch with DB fallback and entity-aware routing."""

import re
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import Alert, Finding
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission
from services.search.service import search_service

router = APIRouter(prefix="/api/v1/search", tags=["search"])

CVE_RE = re.compile(r"CVE-\d{4}-\d+", re.I)
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
HOST_RE = re.compile(r"\b[a-z0-9][a-z0-9.-]+\.[a-z]{2,}\b", re.I)


def classify_entity(query: str) -> dict[str, Any]:
    """Detect entity type for dashboard search routing."""
    q = query.strip()
    ql = q.lower()
    if CVE_RE.search(q):
        return {"type": "cve", "route": "/compliance", "label": "CVE"}
    if IP_RE.search(q):
        return {"type": "ip", "route": "/investigation", "label": "IP address"}
    if HOST_RE.search(q):
        return {"type": "host", "route": "/network", "label": "Host / domain"}
    if any(k in ql for k in ("agent", "orchestrator", "bot")):
        return {"type": "agent", "route": "/agents", "label": "Agent"}
    if any(k in ql for k in ("compliance", "pci", "soc2", "rbi", "dpdp", "grc")):
        return {"type": "compliance", "route": "/compliance", "label": "Compliance"}
    if any(k in ql for k in ("cloud", "s3", "iam", "eks", "aws", "cspm")):
        return {"type": "cloud", "route": "/cloud", "label": "Cloud"}
    if any(k in ql for k in ("hitl", "investigation", "case", "incident")):
        return {"type": "investigation", "route": "/investigation", "label": "Investigation"}
    if any(k in ql for k in ("alert", "finding", "threat")):
        return {"type": "alert", "route": "/alerts", "label": "Alert / finding"}
    return {"type": "keyword", "route": "/alerts", "label": "Keyword"}


@router.get("/{client_id}")
async def search_findings(
    client_id: str,
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
    user: CurrentUser = Depends(require_permission("read:findings")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Entity-aware full-text search across findings and alerts."""
    enforce_tenant(user, client_id)
    entity = classify_entity(q)
    es_hits = await search_service.search(client_id, q, limit=limit)
    if es_hits:
        return {
            "source": "elasticsearch",
            "query": q,
            "entity": entity,
            "results": es_hits,
        }

    pattern = f"%{q}%"
    finding_result = await db.execute(
        select(Finding)
        .where(
            Finding.tenant_id == client_id,
            or_(Finding.title.ilike(pattern), Finding.description.ilike(pattern)),
        )
        .order_by(Finding.created_at.desc())
        .limit(limit)
    )
    alert_result = await db.execute(
        select(Alert)
        .where(
            Alert.tenant_id == client_id,
            or_(Alert.title.ilike(pattern), Alert.source.ilike(pattern)),
        )
        .order_by(Alert.created_at.desc())
        .limit(limit)
    )
    db_hits: list[dict[str, Any]] = []
    for f in finding_result.scalars().all():
        db_hits.append(
            {
                "entity_type": "finding",
                "id": str(f.id),
                "tenant_id": f.tenant_id,
                "agent_id": f.agent_id,
                "severity": f.severity,
                "title": f.title,
                "description": (f.description or "")[:300],
                "confidence": f.confidence,
                "route": "/alerts",
            }
        )
    for a in alert_result.scalars().all():
        db_hits.append(
            {
                "entity_type": "alert",
                "id": str(a.id),
                "tenant_id": a.tenant_id,
                "severity": a.severity,
                "title": a.title,
                "source": a.source,
                "status": a.status,
                "route": "/investigation",
            }
        )
    db_hits.sort(key=lambda h: 0 if h.get("severity") == "critical" else 1)
    return {
        "source": "database",
        "query": q,
        "entity": entity,
        "results": db_hits[:limit],
    }
