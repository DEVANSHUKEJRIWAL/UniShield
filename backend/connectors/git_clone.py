"""Shared git clone helpers for VCS connectors."""

from __future__ import annotations

import re
import shutil
from typing import Callable

import git

_COMMIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def is_commit_sha(ref: str) -> bool:
    return bool(_COMMIT_SHA_RE.fullmatch(ref))


def clone_at_ref(auth_url: str, target_dir: str, ref: str) -> str:
    """Clone a repository and check out a branch name or commit SHA."""
    if is_commit_sha(ref):
        _clone_commit(auth_url, target_dir, ref)
        return target_dir

    try:
        git.Repo.clone_from(auth_url, target_dir, branch=ref, depth=1)
    except git.exc.GitCommandError:
        repo = git.Repo.clone_from(auth_url, target_dir, depth=1)
        repo.git.checkout(ref)
    return target_dir


def _clone_commit(auth_url: str, target_dir: str, sha: str) -> None:
    try:
        repo = git.Repo.clone_from(auth_url, target_dir, multi_options=["--depth", "1"])
        repo.git.fetch("origin", sha, depth=1)
        repo.git.checkout(sha)
    except git.exc.GitCommandError:
        shutil.rmtree(target_dir, ignore_errors=True)
        repo = git.Repo.clone_from(auth_url, target_dir)
        repo.git.checkout(sha)


def make_temp_cleanup(path: str) -> Callable[[], None]:
    def _cleanup() -> None:
        shutil.rmtree(path, ignore_errors=True)

    return _cleanup
