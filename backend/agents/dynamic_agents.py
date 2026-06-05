"""Stub runners for dynamic workflow agents (web, asm, cloudsec)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from backend.memory.shared_memory import SharedMemoryClient

logger = logging.getLogger(__name__)

_AGENT_DEFAULTS = {
    "web": {"risk_score": 45, "highest_severity": "MEDIUM", "critical_count": 0},
    "asm": {"risk_score": 55, "highest_severity": "MEDIUM", "critical_count": 0},
    "cloudsec": {"risk_score": 60, "highest_severity": "HIGH", "critical_count": 1},
}


class DynamicAgentRunner:
    """Minimal decision-surface writers for incident/dynamic workflow agents."""

    def __init__(self, shared_memory: SharedMemoryClient, agent_key: str) -> None:
        self._shared = shared_memory
        self._agent_key = agent_key
        self._defaults = _AGENT_DEFAULTS.get(agent_key, _AGENT_DEFAULTS["web"])

    async def run(self, workflow_id: str, client_id: str, *, context: dict | None = None) -> None:
        ctx = context or {}
        payload = {
            "agent_id": self._agent_key,
            "completed_at": datetime.now(UTC).isoformat(),
            "risk_score": int(ctx.get("risk_score", self._defaults["risk_score"])),
            "highest_severity": ctx.get("highest_severity", self._defaults["highest_severity"]),
            "requires_human_approval": bool(ctx.get("requires_human_approval", False)),
            "auto_remediation_safe": True,
            "forward_to": ctx.get("forward_to", []),
            "critical_count": int(ctx.get("critical_count", self._defaults["critical_count"])),
            "secret_findings_count": 0,
            "correlated_to_incident": bool(ctx.get("correlated_to_incident", True)),
            "summary": f"{self._agent_key.upper()} assessment complete (connect live scanner for production)",
        }
        await self._shared.write_agent_output(workflow_id, self._agent_key, payload)
        logger.info("Dynamic agent %s completed for workflow %s", self._agent_key, workflow_id)
