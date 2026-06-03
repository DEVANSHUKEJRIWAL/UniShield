"""Dataflow analyzer — AST-based taint tracking and call-graph enrichment."""

from __future__ import annotations

import logging
import os
from typing import Any

from unishield.attack_path.ast_extractor import ASTExtractor

logger = logging.getLogger(__name__)


class DataflowAnalyzer:
    """Analyzes data flow and taint propagation using AST call graphs."""

    def __init__(self) -> None:
        self.extractor = ASTExtractor()

    async def run(
        self,
        files: list[str],
        *,
        file_contents: dict[str, str] | None = None,
        language_map: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        language_map = language_map or {}
        contents = dict(file_contents or {})
        enrichments: list[dict[str, Any]] = []

        for file_path in files:
            source = contents.get(file_path) or self._read_file(file_path)
            if not source:
                source = self.extractor._synthetic_stub(file_path)
            lang = language_map.get(file_path, self.extractor._guess_language(file_path))
            file_ast = self.extractor.extract_file(file_path, source, lang)
            if not file_ast.entry_points and not file_ast.call_edges and not file_ast.sink_calls:
                continue

            data_flow: list[str] = []
            if file_ast.entry_points:
                data_flow.append("public_api")
            if any(edge.tainted_args for edge in file_ast.call_edges):
                data_flow.append("user_input")
            if file_ast.sanitizers:
                data_flow.append("sanitize")
            if file_ast.sink_calls:
                data_flow.append("sink")

            enrichments.append(
                {
                    "file_path": file_path,
                    "data_flow": data_flow or ["user_input"],
                    "reachable_from": [ep.route for ep in file_ast.entry_points] or ["public_api"],
                    "file_ast": file_ast.to_dict(),
                }
            )

        logger.debug("Dataflow analyzed %d files (%d enrichments)", len(files), len(enrichments))
        return enrichments

    @staticmethod
    def _read_file(file_path: str) -> str:
        if os.path.isfile(file_path):
            try:
                with open(file_path, encoding="utf-8", errors="replace") as handle:
                    return handle.read()
            except OSError:
                return ""
        return ""
