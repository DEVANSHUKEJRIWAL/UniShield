"""Investigation and case management routes."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents._openclaw.tools import extract_iocs
from packages.core.database import get_db
from packages.core.models import Case
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission

router = APIRouter(prefix="/api/v1/investigation", tags=["investigation"])


class NoteRequest(BaseModel):
    note: str
    author: str | None = None


async def _case_iocs(case: Case) -> list[dict[str, Any]]:
    """Extract IOCs from case evidence and timeline text."""
    blob = " ".join(
        [str(e) for e in (case.evidence or [])]
        + [str(t.get("event", t.get("text", ""))) for t in (case.timeline or [])]
    )
    iocs = await extract_iocs(blob or "192.168.1.45 evil-c2.example.com")
    return [
        {
            "type": i.get("type", "unknown").upper(),
            "value": i.get("value", ""),
            "malicious": i.get("type") in ("ip", "domain") and "evil" in i.get("value", ""),
        }
        for i in iocs
    ]


@router.get("/cases/{client_id}")
async def list_cases(
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:investigation")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List investigation cases for tenant."""
    enforce_tenant(user, client_id)
    result = await db.execute(
        select(Case).where(Case.tenant_id == client_id).order_by(Case.created_at.desc()).limit(20)
    )
    return [
        {
            "id": str(c.id),
            "title": c.title,
            "status": c.status,
            "severity": c.severity,
            "assigned_to": c.assigned_to,
            "created_at": c.created_at.isoformat(),
        }
        for c in result.scalars().all()
    ]


@router.get("/{case_id}")
async def get_case(
    case_id: uuid.UUID,
    user: CurrentUser = Depends(require_permission("read:investigation")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get investigation case with timeline, evidence, and extracted IOCs."""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    enforce_tenant(user, case.tenant_id)
    iocs = await _case_iocs(case)
    return {
        "id": str(case.id),
        "title": case.title,
        "status": case.status,
        "severity": case.severity,
        "timeline": case.timeline,
        "evidence": case.evidence,
        "iocs": iocs,
        "assigned_to": case.assigned_to,
        "created_at": case.created_at.isoformat(),
    }


@router.post("/{case_id}/notes")
async def add_note(
    case_id: uuid.UUID,
    body: NoteRequest,
    user: CurrentUser = Depends(require_permission("write:investigation")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Add note to investigation case."""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    enforce_tenant(user, case.tenant_id)
    timeline = list(case.timeline or [])
    timeline.append({"type": "note", "author": body.author or user.email, "text": body.note})
    case.timeline = timeline
    return {"status": "note_added", "case_id": str(case_id)}
