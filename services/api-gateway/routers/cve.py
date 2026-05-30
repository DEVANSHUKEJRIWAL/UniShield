"""CVE poller API (Week 3)."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import CVERecord
from services.api_gateway.dependencies import CurrentUser, require_permission
from services.cve_poller.service import cve_poller

router = APIRouter(prefix="/api/v1/cve", tags=["cve"])


@router.post("/poll")
async def trigger_cve_poll(
    hours: int = Query(6, ge=1, le=168),
    user: CurrentUser = Depends(require_permission("read:agents")),
) -> dict[str, Any]:
    """Trigger NVD CVE poll and persist records."""
    return await cve_poller.poll_and_store(hours=hours)


@router.get("/recent")
async def list_recent_cves(
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(require_permission("read:findings")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List recently stored CVE records."""
    result = await db.execute(
        select(CVERecord).order_by(CVERecord.updated_at.desc()).limit(limit)
    )
    return [
        {
            "cve_id": r.cve_id,
            "cvss_score": r.cvss_score,
            "severity": r.severity,
            "description": r.description[:200],
            "published": r.published,
        }
        for r in result.scalars().all()
    ]
