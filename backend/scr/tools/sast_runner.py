"""SAST runner — Semgrep + language-specific scanners with regex fallback."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from backend.scr.tools.repo_acquirer import read_repo_file
from backend.scr.tools import scanner_integration as scanners

logger = logging.getLogger(__name__)

# Regex fallback rules (used when subprocess tools unavailable or per-file supplement)
from backend.scr.tools.sast_runner_heuristics import HeuristicSAST  # noqa: E402


class SASTRunner:
    """Runs static analysis via Semgrep/Bandit/gosec/ESLint/Checkov + heuristics."""

    def __init__(self) -> None:
        self._heuristics = HeuristicSAST()

    async def run_repo(
        self,
        repo_path: str,
        *,
        semgrep_configs: list[str],
        languages: set[str],
        frameworks: list[str],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Run repo-level scanners once; return findings and tools invoked."""
        tools: list[str] = []
        tasks: list[tuple[str, Any]] = []

        tasks.append(("semgrep", scanners.run_semgrep_scan(repo_path, semgrep_configs)))
        if "python" in languages:
            tasks.append(("bandit", scanners.run_bandit_scan(repo_path)))
        if "go" in languages:
            tasks.append(("gosec", scanners.run_gosec_scan(repo_path)))
        if "javascript" in languages or "typescript" in languages or "express" in frameworks:
            tasks.append(("eslint", scanners.run_eslint_security(repo_path)))
        if "terraform" in languages or "docker" in languages or "kubernetes" in languages or any(
            f in frameworks for f in ("terraform", "docker", "kubernetes")
        ):
            tasks.append(("checkov", scanners.run_checkov_scan(repo_path)))

        findings: list[dict[str, Any]] = []
        results = await asyncio.gather(*(coro for _, coro in tasks), return_exceptions=True)
        for (tool_name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.warning("%s scan failed: %s", tool_name, result)
                continue
            tools.append(tool_name)
            findings.extend(result)

        findings = self._dedupe(findings)
        logger.info("Repo SAST: %d findings from %s", len(findings), tools)
        return findings, tools

    async def run(
        self,
        files: list[str],
        rule_sets: dict,
        *,
        archive_path: Optional[str] = None,
        language_map: Optional[dict[str, str]] = None,
        repo_findings: list[dict] | None = None,
    ) -> list[dict]:
        """Per-batch SAST: filter repo findings + heuristic supplement for batch files."""
        language_map = language_map or {}
        findings: list[dict] = []

        if repo_findings:
            file_set = set(files)
            findings.extend(f for f in repo_findings if f.get("file_path") in file_set)

        for file_path in files:
            content = read_repo_file(file_path, archive_path)
            lang = language_map.get(file_path, self._heuristics.language_for_path(file_path))
            if content:
                findings.extend(self._heuristics.analyze_content(file_path, content, lang))
            else:
                findings.extend(self._heuristics.analyze_path_hints(file_path, lang))

        return self._dedupe(findings)

    @staticmethod
    def _dedupe(findings: list[dict]) -> list[dict]:
        seen: set[tuple[str, int, str]] = set()
        unique: list[dict] = []
        for finding in findings:
            key = (
                finding.get("file_path", ""),
                finding.get("line_start", finding.get("line_number", 0)),
                finding.get("category", finding.get("rule_id", "")),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(finding)
        return unique
