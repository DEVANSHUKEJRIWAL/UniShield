"""SAST runner — static analysis against cloned repository files."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Optional

from unishield.agents.scr.tools.repo_acquirer import read_repo_file

logger = logging.getLogger(__name__)

CONTENT_RULES: list[tuple[re.Pattern[str], str, str, str, str]] = [
    (re.compile(r"eval\s*\("), "python", "code_execution", "HIGH", "CWE-94"),
    (re.compile(r"exec\s*\("), "python", "code_execution", "HIGH", "CWE-94"),
    (re.compile(r"os\.system\s*\("), "python", "command_injection", "HIGH", "CWE-78"),
    (re.compile(r"subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True"), "python", "command_injection", "HIGH", "CWE-78"),
    (re.compile(r"pickle\.loads\s*\("), "python", "deserialization", "HIGH", "CWE-502"),
    (re.compile(r"yaml\.load\s*\("), "python", "deserialization", "HIGH", "CWE-502"),
    (re.compile(r"(SELECT|INSERT|UPDATE|DELETE).*\{.*\}|f['\"].*(SELECT|INSERT|UPDATE|DELETE)"), "python", "injection", "HIGH", "CWE-89"),
    (re.compile(r"\.execute\s*\(\s*f['\"]"), "python", "injection", "HIGH", "CWE-89"),
    (re.compile(r"innerHTML\s*="), "javascript", "xss", "HIGH", "CWE-79"),
    (re.compile(r"document\.write\s*\("), "javascript", "xss", "MEDIUM", "CWE-79"),
    (re.compile(r"Runtime\.getRuntime\(\)\.exec"), "java", "command_injection", "HIGH", "CWE-78"),
    (re.compile(r"Statement\.execute\s*\(\s*[\"'].*\+"), "java", "injection", "HIGH", "CWE-89"),
]

PATH_HINTS: list[tuple[str, str, str, str]] = [
    ("sql", "injection", "HIGH", "CWE-89"),
    ("xss", "xss", "HIGH", "CWE-79"),
    ("vulnerable", "security", "MEDIUM", "CWE-693"),
    ("ssrf", "ssrf", "HIGH", "CWE-918"),
    ("xxe", "xxe", "HIGH", "CWE-611"),
    ("deserial", "deserialization", "HIGH", "CWE-502"),
    ("command", "command_injection", "HIGH", "CWE-78"),
    ("path-traversal", "path_traversal", "HIGH", "CWE-22"),
    ("idor", "broken_access_control", "MEDIUM", "CWE-639"),
]


class SASTRunner:
    """Runs static analysis rules against source files."""

    async def run(
        self,
        files: list[str],
        rule_sets: dict,
        *,
        archive_path: Optional[str] = None,
        language_map: Optional[dict[str, str]] = None,
    ) -> list[dict]:
        findings: list[dict] = []
        language_map = language_map or {}
        for file_path in files:
            content = read_repo_file(file_path, archive_path)
            if content:
                findings.extend(
                    self._analyze_content(
                        file_path,
                        content,
                        language_map.get(file_path, self._language_for_path(file_path)),
                    )
                )
            else:
                findings.extend(
                    self._analyze_path_hints(
                        file_path,
                        language_map.get(file_path, self._language_for_path(file_path)),
                    )
                )
        logger.debug("SAST found %d findings in %d files", len(findings), len(files))
        return findings

    def _analyze_content(self, file_path: str, content: str, language: str) -> list[dict]:
        findings: list[dict] = []
        lines = content.splitlines()

        for pattern, rule_lang, category, severity, cwe in CONTENT_RULES:
            if rule_lang != "python" and not file_path.lower().endswith(f".{rule_lang[:2]}"):
                if rule_lang == "javascript" and not file_path.lower().endswith((".js", ".jsx", ".ts", ".tsx")):
                    continue
                if rule_lang == "java" and not file_path.lower().endswith(".java"):
                    continue
            for line_no, line in enumerate(lines, start=1):
                if not pattern.search(line):
                    continue
                findings.append(
                    self._finding(
                        file_path=file_path,
                        language=language,
                        line_start=line_no,
                        line_end=line_no,
                        snippet=line.strip()[:240],
                        severity=severity,
                        category=category,
                        rule_id=f"{language}.{category}",
                        cwe_id=cwe,
                    )
                )

        findings.extend(self._analyze_path_hints(file_path, language))
        return self._dedupe(findings)

    def _analyze_path_hints(self, file_path: str, language: str) -> list[dict]:
        lowered = file_path.lower()
        findings: list[dict] = []
        for hint, category, severity, cwe in PATH_HINTS:
            if hint not in lowered:
                continue
            findings.append(
                self._finding(
                    file_path=file_path,
                    language=language,
                    line_start=1,
                    line_end=1,
                    snippet=f"Suspicious path segment: {hint}",
                    severity=severity,
                    category=category,
                    rule_id=f"{language}.path-{category}",
                    cwe_id=cwe,
                )
            )
        return findings

    @staticmethod
    def _language_for_path(file_path: str) -> str:
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        return {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "java": "java",
            "go": "go",
            "rb": "ruby",
        }.get(ext, "unknown")

    @staticmethod
    def _finding(
        *,
        file_path: str,
        language: str,
        line_start: int,
        line_end: int,
        snippet: str,
        severity: str,
        category: str,
        rule_id: str,
        cwe_id: str,
    ) -> dict[str, Any]:
        return {
            "finding_id": str(uuid.uuid4()),
            "file_path": file_path,
            "language": language,
            "line_start": line_start,
            "line_end": line_end,
            "column_start": 0,
            "column_end": max(len(snippet), 1),
            "code_snippet": snippet,
            "severity": severity,
            "confidence": 0.85,
            "category": category,
            "rule_id": rule_id,
            "cwe_id": cwe_id,
        }

    @staticmethod
    def _dedupe(findings: list[dict]) -> list[dict]:
        seen: set[tuple[str, int, str]] = set()
        unique: list[dict] = []
        for finding in findings:
            key = (
                finding["file_path"],
                finding["line_start"],
                finding["category"],
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(finding)
        return unique
