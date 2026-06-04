"""Clone connected repositories and enumerate scannable source files."""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import urlparse

from unishield.agents.scr.schemas.input_schema import SCRAgentInput
from unishield.connectors.git_clone import clone_at_ref, make_temp_cleanup

logger = logging.getLogger(__name__)

SCANNABLE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".java",
    ".rb",
    ".php",
    ".cs",
    ".yaml",
    ".yml",
    ".json",
    ".env",
    ".tf",
    ".sql",
    ".html",
    ".jsp",
    ".xml",
}

SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    "vendor",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "target",
    ".idea",
    ".vscode",
}


def _path_matches_pattern(path: str, pattern: str) -> bool:
    if fnmatch.fnmatch(path, pattern):
        return True
    normalized = pattern.replace("**/", "").replace("/**", "").strip("/")
    if not normalized:
        return False
    segments = path.split("/")
    if normalized in segments:
        return True
    return f"/{normalized}/" in f"/{path}/"


def _should_include(path: str, include_patterns: list[str]) -> bool:
    if not include_patterns or include_patterns == ["**/*"]:
        return True
    return any(_path_matches_pattern(path, pat) for pat in include_patterns)


def _should_exclude(path: str, exclude_patterns: list[str]) -> bool:
    return any(_path_matches_pattern(path, pat) for pat in exclude_patterns)


@dataclass
class AcquisitionResult:
    files: list[str]
    archive_path: Optional[str] = None
    cleanup: Optional[Callable[[], None]] = None


def parse_github_owner_name(repo_url: str) -> tuple[str, str]:
    path = urlparse(repo_url).path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        raise ValueError(f"Cannot parse GitHub owner/name from {repo_url}")
    return parts[0], parts[1]


def build_github_auth_url(repo_url: str, token: str) -> str:
    owner, name = parse_github_owner_name(repo_url)
    return f"https://x-access-token:{token}@github.com/{owner}/{name}.git"


def walk_repo_files(
    root_dir: str,
    *,
    include_patterns: list[str],
    exclude_patterns: list[str],
    max_files: int,
    max_file_size_kb: int,
) -> list[str]:
    files: list[str] = []
    max_bytes = max_file_size_kb * 1024

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIR_NAMES]
        for filename in filenames:
            rel_dir = os.path.relpath(dirpath, root_dir)
            rel_path = filename if rel_dir == "." else f"{rel_dir}/{filename}".replace("\\", "/")
            ext = os.path.splitext(filename)[1].lower()
            if ext and ext not in SCANNABLE_EXTENSIONS and ext not in {".pem", ".key"}:
                continue
            if exclude_patterns and _should_exclude(rel_path, exclude_patterns):
                continue
            if not _should_include(rel_path, include_patterns):
                continue
            full_path = os.path.join(dirpath, filename)
            try:
                if os.path.getsize(full_path) > max_bytes:
                    continue
            except OSError:
                continue
            files.append(rel_path)
            if len(files) >= max_files:
                return files

    return sorted(files)


async def acquire_repo_files(input: SCRAgentInput) -> AcquisitionResult:
    """Clone or walk a repository and return relative file paths."""
    if input.file_paths:
        return AcquisitionResult(files=list(input.file_paths), archive_path=input.archive_path)

    if input.raw_code:
        return AcquisitionResult(files=["inline_source.py"], archive_path=input.archive_path)

    if input.archive_path and os.path.isdir(input.archive_path):
        files = walk_repo_files(
            input.archive_path,
            include_patterns=input.include_patterns,
            exclude_patterns=input.exclude_patterns,
            max_files=input.max_files,
            max_file_size_kb=input.max_file_size_kb,
        )
        return AcquisitionResult(files=files, archive_path=input.archive_path)

    if not input.repo_url or not input.repo_auth_token or not input.repo_ref:
        return AcquisitionResult(files=[])

    tmpdir = tempfile.mkdtemp(prefix="unishield-scr-")
    auth_url = build_github_auth_url(input.repo_url, input.repo_auth_token)

    try:
        await asyncio.to_thread(clone_at_ref, auth_url, tmpdir, input.repo_ref)
    except Exception:
        make_temp_cleanup(tmpdir)()
        logger.exception("Failed to clone %s at ref %s", input.repo_url, input.repo_ref)
        raise

    files = walk_repo_files(
        tmpdir,
        include_patterns=input.include_patterns,
        exclude_patterns=input.exclude_patterns,
        max_files=input.max_files,
        max_file_size_kb=input.max_file_size_kb,
    )
    logger.info("Cloned %s — discovered %d scannable files", input.repo_url, len(files))
    return AcquisitionResult(files=files, archive_path=tmpdir, cleanup=make_temp_cleanup(tmpdir))


def resolve_file_path(file_path: str, archive_path: Optional[str]) -> str:
    if archive_path and not os.path.isabs(file_path):
        return os.path.join(archive_path, file_path)
    return file_path


def read_repo_file(file_path: str, archive_path: Optional[str]) -> str:
    full_path = resolve_file_path(file_path, archive_path)
    if not os.path.isfile(full_path):
        return ""
    try:
        with open(full_path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""
