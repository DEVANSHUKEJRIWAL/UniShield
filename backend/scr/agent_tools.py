"""Python scanner tools exposed to OpenClaw SCR agent in skill-first mode."""

from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

ToolHandler = Callable[..., Awaitable[Any]]

TOOL_CATALOG: list[dict[str, Any]] = [
    {
        "name": "run_acquisition",
        "description": "Clone or acquire repository files for scanning",
        "parameters": {"scan_id": "string", "input": "SCRAgentInput fields"},
    },
    {
        "name": "run_detection",
        "description": "Detect languages, frameworks, and rule sets",
        "parameters": {"scan_id": "string", "files": "list"},
    },
    {
        "name": "run_repo_sast",
        "description": "Run Semgrep SAST across repository",
        "parameters": {"input": "object", "detection": "object"},
    },
    {
        "name": "run_secrets_scan",
        "description": "Run Gitleaks secret detection",
        "parameters": {"input": "object"},
    },
    {
        "name": "run_sbom",
        "description": "Generate SBOM via Syft",
        "parameters": {"input": "object"},
    },
    {
        "name": "run_batch_analysis",
        "description": "Per-batch dataflow and heuristic analysis",
        "parameters": {"batch_files": "list", "batch_id": "string"},
    },
    {
        "name": "run_ai_enrichment",
        "description": "LLM enrichment for CRITICAL/HIGH findings (Stage 7)",
        "parameters": {"findings": "list"},
    },
    {
        "name": "run_threat_intel",
        "description": "Threat intel correlation stage",
        "parameters": {"findings": "list", "input": "object"},
    },
    {
        "name": "run_ranking",
        "description": "Rank and deduplicate findings",
        "parameters": {"findings": "list"},
    },
    {
        "name": "assemble_output",
        "description": "Build SCRAgentOutput and write shared memory",
        "parameters": {"scan_context": "object"},
    },
]


class SCRAgentTools:
    """Registry of async tool handlers backed by existing Python stage implementations."""

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
