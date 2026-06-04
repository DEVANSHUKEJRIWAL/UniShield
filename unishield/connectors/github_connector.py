"""GitHub repo connector."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import git
from github import Auth, Github, GithubException

from unishield.connectors.base_connector import BaseRepoConnector, BranchNotFoundError
from unishield.schemas.repo_schemas import RepoConnection

logger = logging.getLogger(__name__)


class GitHubConnector(BaseRepoConnector):
    """GitHub REST + GitPython clone operations."""

    def _client(self, token: str) -> Github:
        return Github(auth=Auth.Token(token))

    def _full_name(self, connection: RepoConnection) -> str:
        return f"{connection.repo_owner}/{connection.repo_name}"

    async def verify_connection(
        self, connection: RepoConnection, token: str
    ) -> tuple[bool, Optional[str]]:
        try:
            g = self._client(token)
            repo = await asyncio.to_thread(g.get_repo, self._full_name(connection))
            if repo.full_name.lower() != self._full_name(connection).lower():
                return False, "Repo name mismatch"
            return True, None
        except GithubException as exc:
            if exc.status == 401:
                return False, "Token is invalid or expired"
            if exc.status == 403:
                return False, "Token lacks repo read permissions"
            if exc.status == 404:
                return False, "Repo not found — check org/repo name"
            message = getattr(exc, "data", {}) or {}
            return False, f"GitHub API error: {message.get('message', str(exc))}"
        except Exception as exc:
            return False, f"Connection error: {exc}"

    async def get_default_branch(self, connection: RepoConnection, token: str) -> str:
        g = self._client(token)
        repo = await asyncio.to_thread(g.get_repo, self._full_name(connection))
        return repo.default_branch

    async def get_latest_commit(self, connection: RepoConnection, token: str, ref: str) -> str:
        g = self._client(token)
        repo = await asyncio.to_thread(g.get_repo, self._full_name(connection))
        try:
            branch = await asyncio.to_thread(repo.get_branch, ref)
        except GithubException as exc:
            if exc.status == 404:
                raise BranchNotFoundError(ref) from exc
            raise
        return branch.commit.sha

    async def get_diff_files(
        self,
        connection: RepoConnection,
        token: str,
        base_sha: str,
        head_sha: str,
    ) -> list[str]:
        g = self._client(token)
        repo = await asyncio.to_thread(g.get_repo, self._full_name(connection))
        comparison = await asyncio.to_thread(repo.compare, base_sha, head_sha)
        return [f.filename for f in comparison.files]

    async def clone_repo(
        self,
        connection: RepoConnection,
        token: str,
        ref: str,
        target_dir: str,
    ) -> str:
        auth_url = (
            f"https://x-access-token:{token}@github.com/"
            f"{connection.repo_owner}/{connection.repo_name}.git"
        )
        from unishield.connectors.git_clone import clone_at_ref

        await asyncio.to_thread(clone_at_ref, auth_url, target_dir, ref)
        return target_dir

    async def get_file_content(
        self,
        connection: RepoConnection,
        token: str,
        file_path: str,
        ref: str,
    ) -> str:
        g = self._client(token)
        repo = await asyncio.to_thread(g.get_repo, self._full_name(connection))
        content = await asyncio.to_thread(repo.get_contents, file_path, ref=ref)
        if isinstance(content, list):
            raise ValueError(f"{file_path} is a directory")
        return content.decoded_content.decode("utf-8", errors="replace")

    async def list_branches(self, connection: RepoConnection, token: str) -> list[str]:
        g = self._client(token)
        repo = await asyncio.to_thread(g.get_repo, self._full_name(connection))
        branches = await asyncio.to_thread(lambda: list(repo.get_branches()))
        return [b.name for b in branches]

    async def post_pr_comment(
        self,
        connection: RepoConnection,
        token: str,
        pr_number: int,
        body: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
    ) -> None:
        g = self._client(token)
        repo = await asyncio.to_thread(g.get_repo, self._full_name(connection))
        pr = await asyncio.to_thread(repo.get_pull, pr_number)
        if file_path and line_number:
            head_sha = pr.head.sha
            commit = await asyncio.to_thread(repo.get_commit, head_sha)
            await asyncio.to_thread(
                pr.create_review_comment,
                body=body,
                commit=commit,
                path=file_path,
                line=line_number,
            )
        else:
            await asyncio.to_thread(pr.create_issue_comment, body)
