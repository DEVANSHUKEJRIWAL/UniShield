"""Health check routes."""

from __future__ import annotations

import os
import subprocess

from fastapi import APIRouter

from unishield.config.settings import settings

router = APIRouter(tags=["health"])


def _git_revision() -> str | None:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                stderr=subprocess.DEVNULL,
                text=True,
            )
            .strip()
            or None
        )
    except Exception:
        return os.getenv("GIT_COMMIT")


@router.get("/health")
async def health() -> dict:
    scr_runner_configured = False
    cma_runner_configured = False
    reporting_runner_configured = False
    try:
        from unishield.api.main import get_orchestrator

        orch = get_orchestrator()
        scr_runner_configured = orch.scr_runner is not None
        cma_runner_configured = orch.cma_runner is not None
        reporting_runner_configured = orch.reporting_runner is not None
    except Exception:
        pass

    return {
        "status": "ok",
        "service": "unishield-orchestrator",
        "git_revision": _git_revision(),
        "openclaw_mock_mode": settings.openclaw_mock_mode,
        "openclaw_gateway_ws_url": settings.openclaw_gateway_ws_url,
        "scr_runner_configured": scr_runner_configured,
        "cma_runner_configured": cma_runner_configured,
        "reporting_runner_configured": reporting_runner_configured,
        "mode": "mock" if settings.openclaw_mock_mode else "live",
        "features": {
            "repo_clone_scr": True,
            "scr_failure_snapshot": True,
            "scr_finalize_placeholder": True,
        },
    }
