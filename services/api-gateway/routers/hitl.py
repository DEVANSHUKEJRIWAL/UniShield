"""HITL decision routes."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission
from services.hitl_service.models import HITLDecision
from services.hitl_service.service import hitl_service

router = APIRouter(prefix="/api/v1/hitl", tags=["hitl"])


class DecideRequest(BaseModel):
    decision: HITLDecision
    modification: str | None = None
    reasoning: str | None = None
    original: dict[str, Any] | None = None


@router.get("/queue/{client_id}")
async def hitl_queue(
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:alerts")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """HITL work queue for tenant."""
    enforce_tenant(user, client_id)
    return await hitl_service.get_queue(client_id, db)


@router.post("/{action_id}/decide")
async def decide_hitl(
    action_id: str,
    body: DecideRequest,
    client_id: str,
    user: CurrentUser = Depends(require_permission("hitl:decide")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Accept, modify, or reject HITL action."""
    enforce_tenant(user, client_id)
    record = await hitl_service.decide(
        action_id=action_id,
        decision=body.decision,
        analyst_id=user.email,
        tenant_id=client_id,
        db=db,
        modification=body.modification,
        reasoning=body.reasoning,
        original=body.original,
    )
    return {"decision_id": str(record.id), "decision": record.decision}
