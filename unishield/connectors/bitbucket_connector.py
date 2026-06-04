"""Bitbucket repo connector."""

from __future__ import annotations

import asyncio
from typing import Optional

import git
from atlassian import Bitbucket

from unishield.connectors.base_connector import BaseRepoConnector
from unishield.schemas.repo_schemas import RepoConnection


class BitbucketConnector(BaseRepoConnector):
    """Bitbucket Cloud/Server connector."""

    def __init__(self, url: str = "https://api.bitbucket.org", is_cloud: bool = True) -> None:
        self.url = url
        self.is_cloud = is_cloud

    def _parse_token(self, token: str) -> tuple[str, str]:
        parts = token.split(":", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return "x-token-auth", token

    def _client(self, token: str) -> Bitbucket:
        username, password = self._parse_token(token)
        return Bitbucket(url=self.url, username=username, password=password)

    async def verify_connection(
        self, connection: RepoConnection, token: str
    ) -> tuple[bool, Optional[str]]:
        try:
            bb = self._client(token)
            repo = await asyncio.to_thread(
                bb.get_repo,
                connection.repo_owner,
                connection.repo_name,
            )
            return (True, None) if repo else (False, "Repo not found")
        except Exception as exc:
            return False, f"Bitbucket connection error: {exc}"

    async def get_default_branch(self, connection: RepoConnection, token: str) -> str:
        bb = self._client(token)
        repo = await asyncio.to_thread(bb.get_repo, connection.repo_owner, connection.repo_name)
        return repo.get("mainbranch", {}).get("name", "main")

    async def get_latest_commit(self, connection: RepoConnection, token: str, ref: str) -> str:
        bb = self._client(token)
        branch = await asyncio.to_thread(
            bb.get_branch,
            connection.repo_owner,
            connection.repo_name,
            ref,
        )
        return branch["target"]["hash"]

    async def get_diff_files(
        self,
        connection: RepoConnection,
        token: str,
        base_sha: str,
        head_sha: str,
    ) -> list[str]:
        bb = self._client(token)
        diff = await asyncio.to_thread(
            bb.get_diff,
            connection.repo_owner,
            connection.repo_name,
            base_sha,
            head_sha,
        )
        files: list[str] = []
        for block in diff.get("diffs", []):
            for hunk in block.get("hunks", []):
                for segment in hunk.get("segments", []):
                    for line in segment.get("lines", []):
                        if line.get("destination"):
                            files.append(line["destination"])
        return sorted(set(files))

    async def clone_repo(
        self,
        connection: RepoConnection,
        token: str,
        ref: str,
        target_dir: str,
    ) -> str:
        username, password = self._parse_token(token)
        if self.is_cloud:
            auth_url = (
                f"https://{username}:{password}@bitbucket.org/"
                f"{connection.repo_owner}/{connection.repo_name}.git"
            )
        else:
            auth_url = (
                self.url.replace("https://", f"https://{username}:{password}@")
                + f"/scm/{connection.repo_owner}/{connection.repo_name}.git"
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
        bb = self._client(token)
        raw = await asyncio.to_thread(
            bb.get_content_of_file,
            connection.repo_owner,
            connection.repo_name,
            file_path,
            at=ref,
        )
        return raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)

    async def list_branches(self, connection: RepoConnection, token: str) -> list[str]:
        bb = self._client(token)
        branches = await asyncio.to_thread(
            bb.get_branches,
            connection.repo_owner,
            connection.repo_name,
        )
        return [b["name"] for b in branches.get("values", branches if isinstance(branches, list) else [])]

    async def post_pr_comment(
        self,
        connection: RepoConnection,
        token: str,
        pr_number: int,
        body: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
    ) -> None:
        bb = self._client(token)
        payload = {"content": {"raw": body}}
        if file_path and line_number:
            payload["inline"] = {"path": file_path, "to": line_number}
        await asyncio.to_thread(
            bb.create_pull_request_comment,
            connection.repo_owner,
            connection.repo_name,
            pr_number,
            payload,
        )
