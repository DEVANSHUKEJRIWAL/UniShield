"""Clone connected repositories and enumerate scannable source files."""

from __future__ import annotations

import asyncio
import fnmatch
import io
import logging
import os
import tarfile
import tempfile
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import urlparse

import httpx

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


def _resolve_tarball_root(extract_dir: str) -> str:
    entries = [name for name in os.listdir(extract_dir) if name not in {".", ".."}]
    if len(entries) == 1:
        candidate = os.path.join(extract_dir, entries[0])
        if os.path.isdir(candidate):
            return candidate
    return extract_dir


async def download_github_tarball(repo_url: str, token: str, ref: str, target_dir: str) -> str:
    """Download and extract a GitHub repository tarball (no local git required)."""
    owner, name = parse_github_owner_name(repo_url)
    url = f"https://api.github.com/repos/{owner}/{name}/tarball/{ref}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

    with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as archive:
        archive.extractall(target_dir, filter="data")

    root = _resolve_tarball_root(target_dir)
    logger.info("Downloaded GitHub tarball for %s/%s at ref %s", owner, name, ref)
    return root


async def _materialize_repo(input: SCRAgentInput, tmpdir: str) -> str:
    """Clone or download repository contents into tmpdir; return scan root path."""
    auth_url = build_github_auth_url(input.repo_url, input.repo_auth_token)  # type: ignore[arg-type]
    try:
        await asyncio.to_thread(clone_at_ref, auth_url, tmpdir, input.repo_ref)  # type: ignore[arg-type]
        return tmpdir
    except Exception as git_exc:
        logger.warning(
            "Git clone failed for %s@%s (%s) — falling back to GitHub tarball API",
            input.repo_url,
            input.repo_ref,
            git_exc,
        )
        return await download_github_tarball(
            input.repo_url,  # type: ignore[arg-type]
            input.repo_auth_token,  # type: ignore[arg-type]
            input.repo_ref,  # type: ignore[arg-type]
            tmpdir,
        )


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


def git_diff_changed_files(repo_root: str, diff_base: str, diff_head: str) -> list[str]:
    """Return relative paths changed between two refs (incremental scan)."""
    import subprocess

    git_dir = os.path.join(repo_root, ".git")
    if not os.path.isdir(git_dir):
        return []
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", diff_base, diff_head],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if proc.returncode != 0:
            proc = subprocess.run(
                ["git", "diff", "--name-only", f"{diff_base}..{diff_head}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
        if proc.returncode != 0:
            logger.warning("git diff failed: %s", proc.stderr.strip())
            return []
        return [line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()]
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("git diff unavailable: %s", exc)
        return []


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
        logger.warning(
            "Repo scan missing clone inputs (url=%s, ref=%s, token=%s)",
            bool(input.repo_url),
            bool(input.repo_ref),
            bool(input.repo_auth_token),
        )
        return AcquisitionResult(files=[])

    tmpdir = tempfile.mkdtemp(prefix="unishield-scr-")
    cleanup = make_temp_cleanup(tmpdir)
    try:
        root = await _materialize_repo(input, tmpdir)
    except Exception:
        cleanup()
        logger.exception("Failed to acquire %s at ref %s", input.repo_url, input.repo_ref)
        raise

    files = walk_repo_files(
        root,
        include_patterns=input.include_patterns,
        exclude_patterns=input.exclude_patterns,
        max_files=input.max_files,
        max_file_size_kb=input.max_file_size_kb,
    )
    logger.info("Acquired %s — discovered %d scannable files", input.repo_url, len(files))
    return AcquisitionResult(files=files, archive_path=root, cleanup=cleanup)


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
