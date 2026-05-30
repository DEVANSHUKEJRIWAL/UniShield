"""Findings API — paginated list and detail (Week 5)."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import Finding
from packages.core.pagination import paginate
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, get_current_user, require_permission

router = APIRouter(prefix="/api/v1/findings", tags=["findings"])


@router.get("/{client_id}")
async def list_findings(
    client_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: str | None = None,
    agent_id: str | None = None,
    user: CurrentUser = Depends(require_permission("read:findings")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Paginated findings for tenant."""
    enforce_tenant(user, client_id)
    meta = paginate(0, page, page_size)
    q = select(Finding).where(Finding.tenant_id == client_id)
    count_q = select(func.count()).select_from(Finding).where(Finding.tenant_id == client_id)
    if severity:
        q = q.where(Finding.severity == severity)
        count_q = count_q.where(Finding.severity == severity)
    if agent_id:
        q = q.where(Finding.agent_id == agent_id)
        count_q = count_q.where(Finding.agent_id == agent_id)
    total = await db.scalar(count_q) or 0
    meta = paginate(total, page, page_size)
    result = await db.execute(
        q.order_by(Finding.created_at.desc()).offset(meta["offset"]).limit(meta["page_size"])
    )
    items = [
        {
            "id": str(f.id),
            "agent_id": f.agent_id,
            "type": f.type,
            "severity": f.severity,
            "confidence": f.confidence,
            "title": f.title,
            "description": f.description[:500],
            "created_at": f.created_at.isoformat(),
        }
        for f in result.scalars().all()
    ]
    return {**meta, "total": total, "items": items}


@router.get("/{client_id}/{finding_id}")
async def get_finding(
    client_id: str,
    finding_id: uuid.UUID,
    user: CurrentUser = Depends(require_permission("read:findings")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Single finding detail."""
    enforce_tenant(user, client_id)
    result = await db.execute(
        select(Finding).where(Finding.id == finding_id, Finding.tenant_id == client_id)
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return {
        "id": str(finding.id),
        "tenant_id": finding.tenant_id,
        "agent_id": finding.agent_id,
        "type": finding.type,
        "severity": finding.severity,
        "confidence": finding.confidence,
        "title": finding.title,
        "description": finding.description,
        "reasoning_summary": finding.reasoning_summary,
        "evidence_references": finding.evidence_references,
        "mitre_ttps": finding.mitre_ttps,
        "contributing_agents": finding.contributing_agents,
        "raw_output": finding.raw_output,
        "created_at": finding.created_at.isoformat(),
    }
