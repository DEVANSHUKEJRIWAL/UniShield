"""Knowledge graph API routes."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission
from services.knowledge_graph.service import kg_service

router = APIRouter(prefix="/api/v1/kg", tags=["knowledge-graph"])


class NLQueryRequest(BaseModel):
    query: str
    client_id: str


@router.get("/blast-radius/{entity_id}")
async def blast_radius(
    entity_id: str,
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:agents")),
) -> dict[str, Any]:
    """Blast radius for entity."""
    enforce_tenant(user, client_id)
    return await kg_service.blast_radius(entity_id, client_id)


@router.get("/attack-paths/{incident_id}")
async def attack_paths(
    incident_id: str,
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:agents")),
) -> dict[str, Any]:
    """Attack paths for incident."""
    enforce_tenant(user, client_id)
    return await kg_service.attack_paths(incident_id, client_id)


@router.post("/query")
async def nl_query(
    body: NLQueryRequest,
    user: CurrentUser = Depends(require_permission("read:agents")),
) -> dict[str, Any]:
    """Natural language KG query."""
    enforce_tenant(user, body.client_id)
    return await kg_service.nl_query(body.query, body.client_id)
