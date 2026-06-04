"""Stage 1 — file acquisition and filtering."""

from __future__ import annotations

import logging

from unishield.agents.scr.schemas.input_schema import SCRAgentInput
from unishield.agents.scr.schemas.input_schema import ScanMode
from unishield.agents.scr.tools.repo_acquirer import (
    AcquisitionResult,
    acquire_repo_files,
    git_diff_changed_files,
    walk_repo_files,
    _should_exclude,
    _should_include,
)
from unishield.memory.personal_memory import PersonalMemoryClient

logger = logging.getLogger(__name__)


class AcquisitionStage:
    """Acquires and filters source files for scanning."""

    def __init__(self, personal_memory: PersonalMemoryClient) -> None:
        self._memory = personal_memory

    async def run(self, scan_id: str, input: SCRAgentInput) -> AcquisitionResult:
        if input.file_paths:
            files = self._apply_filters(list(input.file_paths), input)
            files = files[: input.max_files]
            await self._memory.save_file_list(scan_id, files)
            logger.info("Acquisition: %d files after filtering", len(files))
            return AcquisitionResult(files=files, archive_path=input.archive_path)

        if input.raw_code:
            files = self._apply_filters(["inline_source.py"], input)
            await self._memory.save_file_list(scan_id, files)
            return AcquisitionResult(files=files, archive_path=input.archive_path)

        if input.archive_path:
            files = walk_repo_files(
                input.archive_path,
                include_patterns=input.include_patterns,
                exclude_patterns=input.exclude_patterns,
                max_files=input.max_files,
                max_file_size_kb=input.max_file_size_kb,
            )
            files = self._apply_filters(files, input)
            await self._memory.save_file_list(scan_id, files)
            logger.info("Acquisition: %d files from archive_path", len(files))
            return AcquisitionResult(files=files, archive_path=input.archive_path)

        if input.repo_url:
            result = await acquire_repo_files(input)
            files = self._apply_filters(result.files, input)
            if (
                str(input.scan_mode) == ScanMode.INCREMENTAL.value
                and input.diff_base
                and input.diff_head
                and result.archive_path
            ):
                changed = git_diff_changed_files(result.archive_path, input.diff_base, input.diff_head)
                if changed:
                    changed_set = set(changed)
                    files = [f for f in files if f in changed_set or any(f.endswith(c) for c in changed)]
                    logger.info("Incremental scan: %d changed files", len(files))
            files = files[: input.max_files]
            await self._memory.save_file_list(scan_id, files)
            logger.info("Acquisition: %d files after filtering", len(files))
            return AcquisitionResult(
                files=files,
                archive_path=result.archive_path,
                cleanup=result.cleanup,
            )

        await self._memory.save_file_list(scan_id, [])
        return AcquisitionResult(files=[])

    def _apply_filters(self, files: list[str], input: SCRAgentInput) -> list[str]:
        result = []
        for path in files:
            if input.exclude_patterns and _should_exclude(path, input.exclude_patterns):
                continue
            if not _should_include(path, input.include_patterns):
                continue
            result.append(path)
        return result
