"""Investigation and case management routes."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import Case
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, get_current_user

router = APIRouter(prefix="/api/v1/investigation", tags=["investigation"])


class NoteRequest(BaseModel):
    note: str
    author: str | None = None


@router.get("/cases/{client_id}")
async def list_cases(
    client_id: str,
    user: CurrentUser = Depends(get_current_user),
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
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get investigation case with timeline and evidence."""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    enforce_tenant(user, case.tenant_id)
    return {
        "id": str(case.id),
        "title": case.title,
        "status": case.status,
        "severity": case.severity,
        "timeline": case.timeline,
        "evidence": case.evidence,
        "assigned_to": case.assigned_to,
        "created_at": case.created_at.isoformat(),
    }


@router.post("/{case_id}/notes")
async def add_note(
    case_id: uuid.UUID,
    body: NoteRequest,
    user: CurrentUser = Depends(get_current_user),
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
