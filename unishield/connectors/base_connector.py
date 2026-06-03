"""Abstract base for VCS repo connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from unishield.schemas.repo_schemas import RepoConnection


class BaseRepoConnector(ABC):
    """Provider-agnostic repo connector interface."""

    @abstractmethod
    async def verify_connection(
        self, connection: RepoConnection, token: str
    ) -> tuple[bool, Optional[str]]:
        """Test read access. Returns (success, error_message)."""

    @abstractmethod
    async def get_default_branch(self, connection: RepoConnection, token: str) -> str:
        """Return default branch name."""

    @abstractmethod
    async def get_latest_commit(self, connection: RepoConnection, token: str, ref: str) -> str:
        """Return latest commit SHA for ref."""

    @abstractmethod
    async def get_diff_files(
        self,
        connection: RepoConnection,
        token: str,
        base_sha: str,
        head_sha: str,
    ) -> list[str]:
        """Return changed file paths between two commits."""

    @abstractmethod
    async def clone_repo(
        self,
        connection: RepoConnection,
        token: str,
        ref: str,
        target_dir: str,
    ) -> str:
        """Clone repo to target_dir; return path."""

    @abstractmethod
    async def get_file_content(
        self,
        connection: RepoConnection,
        token: str,
        file_path: str,
        ref: str,
    ) -> str:
        """Return file contents at ref."""

    @abstractmethod
    async def list_branches(self, connection: RepoConnection, token: str) -> list[str]:
        """List branch names."""

    @abstractmethod
    async def post_pr_comment(
        self,
        connection: RepoConnection,
        token: str,
        pr_number: int,
        body: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
    ) -> None:
        """Post PR/MR comment (inline or general)."""
