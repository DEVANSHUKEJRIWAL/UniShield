"""Dataflow analyzer — AST taint tracking with source→sink path detection."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from backend.attack_path.ast_extractor import ASTExtractor

logger = logging.getLogger(__name__)

TAINT_SOURCES = ("request", "input", "params", "query", "body", "env", "argv", "cookie", "header")
TAINT_SINKS = ("execute", "system", "eval", "exec", "query", "sql", "shell", "log", "write", "render")
SANITIZERS = ("escape", "sanitize", "validate", "quote", "bind", "parameter", "htmlspecialchars", "encode")


class DataflowAnalyzer:
    """Analyzes data flow and flags taint paths without sanitizers."""

    def __init__(self) -> None:
        self.extractor = ASTExtractor()

    async def run(
        self,
        files: list[str],
        *,
        file_contents: dict[str, str] | None = None,
        language_map: dict[str, str] | None = None,
        archive_path: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return enrichments and optional taint findings."""
        language_map = language_map or {}
        contents = dict(file_contents or {})
        enrichments: list[dict[str, Any]] = []
        taint_findings: list[dict[str, Any]] = []

        for file_path in files:
            source = contents.get(file_path) or self._read_file(file_path, archive_path)
            if not source:
                source = self.extractor._synthetic_stub(file_path)
            lang = language_map.get(file_path, self.extractor._guess_language(file_path))
            file_ast = self.extractor.extract_file(file_path, source, lang)

            data_flow: list[str] = []
            if file_ast.entry_points:
                data_flow.append("public_api")
            has_tainted = any(edge.tainted_args for edge in file_ast.call_edges)
            if has_tainted or self._text_has_source(source):
                data_flow.append("user_input")
            has_sanitizer = bool(file_ast.sanitizers) or self._text_has_sanitizer(source)
            if has_sanitizer:
                data_flow.append("sanitize")
            if file_ast.sink_calls or self._text_has_sink(source):
                data_flow.append("sink")

            reachable = [ep.route for ep in file_ast.entry_points] or (
                ["public_api"] if "user_input" in data_flow else []
            )

            enrichments.append(
                {
                    "file_path": file_path,
                    "data_flow": data_flow or ["user_input"],
                    "reachable_from": reachable,
                    "file_ast": file_ast.to_dict(),
                }
            )

            if "user_input" in data_flow and "sink" in data_flow and "sanitize" not in data_flow:
                line = self._first_sink_line(source)
                taint_findings.append(
                    {
                        "finding_id": str(uuid.uuid4()),
                        "file_path": file_path,
                        "language": lang,
                        "line_start": line,
                        "line_end": line,
                        "code_snippet": self._line_at(source, line)[:500],
                        "severity": "HIGH",
                        "confidence": 0.7,
                        "category": "taint_flow",
                        "rule_id": "dataflow.unsanitized_source_to_sink",
                        "cwe_id": "CWE-20",
                        "data_flow": data_flow,
                        "reachable_from": reachable,
                        "tool": "dataflow",
                    }
                )

        logger.debug(
            "Dataflow analyzed %d files (%d enrichments, %d taint findings)",
            len(files),
            len(enrichments),
            len(taint_findings),
        )
        return enrichments, taint_findings

    @staticmethod
    def _read_file(file_path: str, archive_path: str | None) -> str:
        from backend.scr.tools.repo_acquirer import read_repo_file

        if archive_path:
            return read_repo_file(file_path, archive_path)
        if os.path.isfile(file_path):
            try:
                with open(file_path, encoding="utf-8", errors="replace") as handle:
                    return handle.read()
            except OSError:
                return ""
        return ""

    @staticmethod
    def _text_has_source(text: str) -> bool:
        lowered = text.lower()
        return any(src in lowered for src in TAINT_SOURCES)

    @staticmethod
    def _text_has_sink(text: str) -> bool:
        lowered = text.lower()
        return any(sink in lowered for sink in TAINT_SINKS)

    @staticmethod
    def _text_has_sanitizer(text: str) -> bool:
        lowered = text.lower()
        return any(s in lowered for s in SANITIZERS)

    @staticmethod
    def _first_sink_line(text: str) -> int:
        for idx, line in enumerate(text.splitlines(), start=1):
            lowered = line.lower()
            if any(s in lowered for s in TAINT_SINKS):
                return idx
        return 1

    @staticmethod
    def _line_at(text: str, line_no: int) -> str:
        lines = text.splitlines()
        if 1 <= line_no <= len(lines):
            return lines[line_no - 1]
        return ""
