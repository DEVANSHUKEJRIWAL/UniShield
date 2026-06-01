"""Phase 2 BFSI scan API routes."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from packages.phase2.dark_web import run_dark_web_scan
from packages.phase2.insider import run_insider_scan
from packages.phase2.source_code import run_mythos_review

router = APIRouter(prefix="/api/v1", tags=["bfsi"])


class MythosReviewRequest(BaseModel):
    code: str = ""
    language: str = "python"
    filename: str = "snippet.py"
    industry: str = "banking"
    repo_path: str | None = None


class DarkWebScanRequest(BaseModel):
    domain: str
    brand: str = ""
    industry: str = "banking"
    tenant_id: str = "meridian-financial"


class InsiderScanRequest(BaseModel):
    org: str = "meridian-financial"
    industry: str = "banking"
    user_id: str | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    tenant_id: str = "meridian-financial"


class OrchestratorScanRequest(BaseModel):
    domain: str = "meridian.com"
    brand: str = ""
    industry: str = "banking"
    user_id: str | None = None
    tenant_id: str = "meridian-financial"
    code: str = ""
    language: str = "python"
    filename: str = "snippet.py"
    repo_path: str | None = None


@router.post("/mythos-review")
async def mythos_review(request: MythosReviewRequest) -> dict[str, Any]:
    """BFSI source code review — SAST + optional Claude synthesis."""
    return await run_mythos_review(
        request.code,
        request.language,
        request.filename,
        request.industry,
        repo_path=request.repo_path,
    )


@router.post("/darkweb/scan")
async def darkweb_scan(request: DarkWebScanRequest) -> dict[str, Any]:
    """Dark web / external intel scan returning BFSI findings."""
    brand = request.brand or request.domain.split(".")[0]
    return await run_dark_web_scan(request.domain, brand, request.industry, request.tenant_id)


@router.post("/insider/scan")
async def insider_scan(request: InsiderScanRequest) -> dict[str, Any]:
    """Insider threat scan with rule engine and optional live ingest."""
    return await run_insider_scan(
        request.org,
        request.industry,
        request.user_id,
        request.events,
        request.tenant_id,
    )


@router.post("/orchestrator/scan")
async def orchestrator_scan(request: OrchestratorScanRequest) -> dict[str, Any]:
    """Run dark web, source code, and insider scans in one request."""
    brand = request.brand or request.domain.split(".")[0]
    dark = await run_dark_web_scan(request.domain, brand, request.industry, request.tenant_id)
    code = await run_mythos_review(
        request.code,
        request.language,
        request.filename,
        request.industry,
        repo_path=request.repo_path,
    )
    insider = await run_insider_scan(
        request.tenant_id,
        request.industry,
        request.user_id,
        [],
        request.tenant_id,
    )
    return {
        "darkweb": dark,
        "source_code": code,
        "insider": insider,
        "summary": {
            "total_findings": (
                dark.get("summary", {}).get("total", 0)
                + code.get("summary", {}).get("total", 0)
                + insider.get("summary", {}).get("total", 0)
            ),
        },
    }
