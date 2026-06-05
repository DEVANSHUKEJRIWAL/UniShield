"""GitLab repo connector."""

from __future__ import annotations

import asyncio
from typing import Optional

import git
import gitlab
from gitlab.exceptions import GitlabAuthenticationError, GitlabGetError

from backend.connectors.base_connector import BaseRepoConnector
from backend.schemas.repo_schemas import RepoConnection


class GitLabConnector(BaseRepoConnector):
    """GitLab REST + GitPython clone operations."""

    def __init__(self, base_url: str = "https://gitlab.com") -> None:
        self.base_url = base_url.rstrip("/")

    def _project_path(self, connection: RepoConnection) -> str:
        return f"{connection.repo_owner}/{connection.repo_name}"

    def _client(self, token: str) -> gitlab.Gitlab:
        return gitlab.Gitlab(self.base_url, private_token=token)

    async def verify_connection(
        self, connection: RepoConnection, token: str
    ) -> tuple[bool, Optional[str]]:
        try:
            gl = self._client(token)
            await asyncio.to_thread(gl.projects.get, self._project_path(connection))
            return True, None
        except GitlabAuthenticationError:
            return False, "Token is invalid or expired"
        except GitlabGetError as exc:
            return False, f"GitLab API error: {exc.error_message}"
        except Exception as exc:
            return False, f"Connection error: {exc}"

    async def get_default_branch(self, connection: RepoConnection, token: str) -> str:
        gl = self._client(token)
        project = await asyncio.to_thread(gl.projects.get, self._project_path(connection))
        return project.default_branch

    async def get_latest_commit(self, connection: RepoConnection, token: str, ref: str) -> str:
        gl = self._client(token)
        project = await asyncio.to_thread(gl.projects.get, self._project_path(connection))
        branch = await asyncio.to_thread(project.branches.get, ref)
        return branch.commit["id"]

    async def get_diff_files(
        self,
        connection: RepoConnection,
        token: str,
        base_sha: str,
        head_sha: str,
    ) -> list[str]:
        gl = self._client(token)
        project = await asyncio.to_thread(gl.projects.get, self._project_path(connection))
        compare = await asyncio.to_thread(project.repository_compare, base_sha, head_sha)
        diffs = compare.get("diffs", [])
        return [d["new_path"] for d in diffs if d.get("new_path")]

    async def clone_repo(
        self,
        connection: RepoConnection,
        token: str,
        ref: str,
        target_dir: str,
    ) -> str:
        host = self.base_url.replace("https://", "")
        auth_url = f"https://oauth2:{token}@{host}/{self._project_path(connection)}.git"
        from backend.connectors.git_clone import clone_at_ref

        await asyncio.to_thread(clone_at_ref, auth_url, target_dir, ref)
        return target_dir

    async def get_file_content(
        self,
        connection: RepoConnection,
        token: str,
        file_path: str,
        ref: str,
    ) -> str:
        gl = self._client(token)
        project = await asyncio.to_thread(gl.projects.get, self._project_path(connection))
        file_obj = await asyncio.to_thread(project.files.get, file_path, ref=ref)
        return file_obj.decode().decode("utf-8", errors="replace")

    async def list_branches(self, connection: RepoConnection, token: str) -> list[str]:
        gl = self._client(token)
        project = await asyncio.to_thread(gl.projects.get, self._project_path(connection))
        branches = await asyncio.to_thread(project.branches.list, all=True)
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
        gl = self._client(token)
        project = await asyncio.to_thread(gl.projects.get, self._project_path(connection))
        mr = await asyncio.to_thread(project.mergerequests.get, pr_number)
        if file_path and line_number:
            await asyncio.to_thread(
                mr.discussions.create,
                {"body": body, "position": {"base_sha": mr.diff_refs["base_sha"], "new_path": file_path, "new_line": line_number}},
            )
        else:
            await asyncio.to_thread(mr.notes.create, {"body": body})
