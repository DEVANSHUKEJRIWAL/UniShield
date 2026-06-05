"""Attack path API — optional Neo4j-backed graph summary."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/attack-path", tags=["attack-path"])


@router.get("/{workflow_id}")
async def get_attack_path_summary(workflow_id: str) -> dict:
    from backend.api.main import get_postgres, get_shared_memory

    shared = get_shared_memory()
    if await shared.workflow_exists(workflow_id):
        snapshot = await shared.get_full_snapshot(workflow_id)
        scr = snapshot.get("scr") or {}
        summary = scr.get("attack_paths_summary") or {}
        neo4j_url = scr.get("neo4j_query_url")
        return {
            "workflow_id": workflow_id,
            "attack_paths_summary": summary,
            "neo4j_browser_url": neo4j_url,
            "source": "shared_memory",
        }

    postgres = get_postgres()
    row = await postgres.fetchrow(
        "SELECT snapshot FROM workflow_outputs WHERE workflow_id = $1",
        workflow_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Workflow output not found")
    snapshot = row["snapshot"]
    scr = (snapshot or {}).get("scr") or {}
    return {
        "workflow_id": workflow_id,
        "attack_paths_summary": scr.get("attack_paths_summary") or {},
        "neo4j_browser_url": scr.get("neo4j_query_url"),
        "source": "database",
    }
