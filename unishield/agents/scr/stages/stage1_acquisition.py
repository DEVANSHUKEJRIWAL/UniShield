"""Stage 1 — file acquisition and filtering."""

from __future__ import annotations

import fnmatch
import logging
import os

from unishield.agents.scr.schemas.input_schema import SCRAgentInput
from unishield.memory.personal_memory import PersonalMemoryClient

logger = logging.getLogger(__name__)


class AcquisitionStage:
    """Acquires and filters source files for scanning."""

    def __init__(self, personal_memory: PersonalMemoryClient) -> None:
        self._memory = personal_memory

    async def run(self, scan_id: str, input: SCRAgentInput) -> list[str]:
        if input.file_paths:
            files = list(input.file_paths)
        elif input.raw_code:
            files = ["inline_source.py"]
        elif input.repo_url:
            files = [
                "src/main.py",
                "src/auth/login.py",
                "tests/test_auth.py",
                "vendor/lib.py",
            ]
        else:
            files = []

        filtered = self._apply_filters(files, input)
        filtered = filtered[: input.max_files]
        await self._memory.save_file_list(scan_id, filtered)
        logger.info("Acquisition: %d files after filtering", len(filtered))
        return filtered

    def _apply_filters(self, files: list[str], input: SCRAgentInput) -> list[str]:
        result = []
        for path in files:
            if input.exclude_patterns and any(
                fnmatch.fnmatch(path, pat) for pat in input.exclude_patterns
            ):
                continue
            if input.include_patterns and not any(
                fnmatch.fnmatch(path, pat) for pat in input.include_patterns
            ):
                continue
            result.append(path)
        return result
