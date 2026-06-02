"""Dataflow analyzer — taint tracking (stub)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class DataflowAnalyzer:
    """Analyzes data flow and taint propagation in source files."""

    async def run(self, files: list[str]) -> list[dict]:
        enrichments: list[dict] = []
        for file_path in files:
            if "auth" in file_path.lower():
                enrichments.append(
                    {
                        "file_path": file_path,
                        "data_flow": ["user_input", "sanitize", "database"],
                        "reachable_from": ["public_api"],
                    }
                )
        logger.debug("Dataflow analyzed %d files", len(files))
        return enrichments
