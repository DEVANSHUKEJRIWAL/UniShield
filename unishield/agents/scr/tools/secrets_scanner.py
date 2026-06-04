"""Secrets scanner — detects leaked credentials in repository files."""

from __future__ import annotations

import logging
import re
from typing import Optional

from unishield.agents.scr.tools.repo_acquirer import read_repo_file

logger = logging.getLogger(__name__)

SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]"), "generic_secret"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "openai_api_key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{20,}"), "github_pat"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws_access_key"),
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private_key"),
]


class SecretsScanner:
    """Scans files for leaked secrets and credentials."""

    async def run(self, files: list[str], *, archive_path: Optional[str] = None) -> list[dict]:
        findings: list[dict] = []
        for file_path in files:
            content = read_repo_file(file_path, archive_path)
            if not content:
                if "secret" in file_path.lower() or file_path.endswith(".env"):
                    findings.append(self._path_only_finding(file_path))
                continue
            for line_no, line in enumerate(content.splitlines(), start=1):
                for pattern, secret_type in SECRET_PATTERNS:
                    match = pattern.search(line)
                    if not match:
                        continue
                    masked = match.group(0)
                    if len(masked) > 8:
                        masked = masked[:4] + "****" + masked[-4:]
                    findings.append(
                        {
                            "secret_type": secret_type,
                            "file_path": file_path,
                            "line_number": line_no,
                            "masked_value": masked,
                            "entropy_score": 4.5,
                            "verified_live": False,
                            "git_history_exposed": True,
                        }
                    )
        logger.debug("Secrets scan found %d findings", len(findings))
        return findings

    @staticmethod
    def _path_only_finding(file_path: str) -> dict:
        return {
            "secret_type": "api_key",
            "file_path": file_path,
            "line_number": 1,
            "masked_value": "****",
            "entropy_score": 4.0,
            "verified_live": False,
            "git_history_exposed": True,
        }
