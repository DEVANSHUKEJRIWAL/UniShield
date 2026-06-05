"""Python scanner tools exposed to OpenClaw SCR agent in skill-first mode."""

from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

ToolHandler = Callable[..., Awaitable[Any]]

TOOL_CATALOG: list[dict[str, Any]] = [
    {"name": "run_acquisition", "description": "Clone or acquire repository files for scanning"},
    {"name": "run_detection", "description": "Detect languages, frameworks, and rule sets"},
    {"name": "run_repo_scans", "description": "Run Semgrep SAST, Gitleaks secrets, and Syft SBOM"},
    {"name": "run_batch_analysis", "description": "Per-batch dataflow and heuristic analysis"},
    {"name": "run_ai_enrichment", "description": "LLM enrichment for CRITICAL/HIGH findings (Stage 7)"},
    {"name": "run_threat_intel", "description": "Threat intel correlation stage"},
    {"name": "run_ranking", "description": "Rank and deduplicate findings"},
    {"name": "run_attack_path", "description": "Build attack path graph summary"},
    {"name": "assemble_output", "description": "Build SCRAgentOutput and write shared memory + agent.complete"},
]


class SCRAgentTools:
    """Registry of async tool handlers backed by Python stage implementations."""

    def __init__(self) -> None:
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, name: str, handler: ToolHandler) -> None:
        self._handlers[name] = handler

    def catalog(self) -> list[dict[str, Any]]:
        return TOOL_CATALOG

    async def invoke(self, name: str, **kwargs: Any) -> Any:
        handler = self._handlers.get(name)
        if not handler:
            raise KeyError(f"Unknown SCR tool: {name}")
        logger.info("SCR tool invoke: %s", name)
        return await handler(**kwargs)
