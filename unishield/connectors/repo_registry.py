"""Persistent repo connection registry."""

from __future__ import annotations

import asyncio
import json
import tempfile
import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from unishield.config.settings import Settings, settings
from unishield.connectors.bitbucket_connector import BitbucketConnector
from unishield.connectors.github_connector import GitHubConnector
from unishield.connectors.gitlab_connector import GitLabConnector
from unishield.infrastructure.postgres_client import PostgresClient
from unishield.infrastructure.vault_client import VaultClient
from unishield.schemas.repo_schemas import (
    MultiRepoScanRequest,
    RepoConnection,
    RepoConnectionCreate,
    RepoScanTarget,
    RepoStatus,
)


class RepoNotConnectedError(Exception):
    """Raised when a repo connection is not in CONNECTED state."""


def _pg_timestamp(value: datetime | None) -> datetime | None:
    """Normalize datetimes for Postgres TIMESTAMP (without time zone) columns."""
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _from_pg_timestamp(value: datetime | None) -> datetime | None:
    """Attach UTC when reading naive timestamps from Postgres."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


REPO_CONNECTIONS_DDL = """
CREATE TABLE IF NOT EXISTS repo_connections (
    connection_id       VARCHAR(100) PRIMARY KEY,
    client_id           VARCHAR(100) NOT NULL,
    provider            VARCHAR(50)  NOT NULL,
    auth_method         VARCHAR(50)  NOT NULL,
    repo_url            TEXT         NOT NULL,
    repo_owner          VARCHAR(200) NOT NULL,
    repo_name           VARCHAR(200) NOT NULL,
    default_branch      VARCHAR(200) NOT NULL DEFAULT 'main',
    vault_secret_path   TEXT         NOT NULL,
    description         TEXT,
    is_crown_jewel      BOOLEAN      NOT NULL DEFAULT FALSE,
    crown_jewel_paths   JSONB        NOT NULL DEFAULT '[]',
    exclude_patterns    JSONB        NOT NULL DEFAULT '[]',
    include_languages   JSONB        NOT NULL DEFAULT '[]',
    status              VARCHAR(50)  NOT NULL DEFAULT 'pending',
    last_verified_at    TIMESTAMP,
    last_scanned_at     TIMESTAMP,
    last_scan_id        VARCHAR(100),
    error_message       TEXT,
    registered_at       TIMESTAMP    NOT NULL,
    registered_by       VARCHAR(100) NOT NULL,
    updated_at          TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rc_client ON repo_connections(client_id);
CREATE INDEX IF NOT EXISTS idx_rc_status ON repo_connections(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rc_url_client ON repo_connections(client_id, repo_url);
"""


class RepoRegistry:
    """Central registry for registered repo connections."""

    def __init__(
        self,
        postgres: PostgresClient,
        vault_client: VaultClient,
        app_settings: Settings | None = None,
    ) -> None:
        self._postgres = postgres
        self._vault = vault_client
        self._settings = app_settings or settings
        self._connectors = {
            "github": GitHubConnector(),
            "gitlab": GitLabConnector(base_url=self._settings.gitlab_base_url),
            "bitbucket": BitbucketConnector(
                url=self._settings.bitbucket_url,
                is_cloud=self._settings.bitbucket_is_cloud,
            ),
        }

    async def init_schema(self) -> None:
        statements = [
            s.strip()
            for s in REPO_CONNECTIONS_DDL.split(";")
            if s.strip()
        ]
        async with self._postgres.pool.acquire() as conn:
            for statement in statements:
                await conn.execute(statement)

    async def ensure_schema(self) -> None:
        """Idempotent schema init — safe to call before repo operations."""
        await self.init_schema()

    async def register(
        self,
        payload: RepoConnectionCreate,
        token: str,
    ) -> RepoConnection:
        existing = await self._postgres.fetchrow(
            "SELECT connection_id FROM repo_connections WHERE client_id = $1 AND repo_url = $2",
            payload.client_id,
            payload.repo_url,
        )
        connection_id = existing["connection_id"] if existing else str(uuid.uuid4())
        vault_path = f"secret/unishield/{payload.client_id}/{connection_id}"
        now = datetime.now(UTC)
        connection = RepoConnection(
            connection_id=connection_id,
            client_id=payload.client_id,
            provider=payload.provider,
            auth_method=payload.auth_method,
            repo_url=payload.repo_url,
            repo_owner=payload.repo_owner,
            repo_name=payload.repo_name,
            default_branch=payload.default_branch,
            vault_secret_path=vault_path,
            description=payload.description,
            is_crown_jewel=payload.is_crown_jewel,
            crown_jewel_paths=payload.crown_jewel_paths,
            exclude_patterns=payload.exclude_patterns,
            include_languages=payload.include_languages,
            registered_at=now,
            registered_by=payload.registered_by,
        )
        await self._write_vault_secret(vault_path, token)
        connector = self._connectors[str(payload.provider)]
        success, error = await connector.verify_connection(connection, token)
        connection.status = RepoStatus.CONNECTED if success else RepoStatus.AUTH_FAILED
        connection.last_verified_at = now
        connection.error_message = error
        if success and not payload.default_branch:
            try:
                connection.default_branch = await connector.get_default_branch(connection, token)
            except Exception:
                pass
        await self._upsert_connection(connection)
        return connection

    async def verify_connection(self, connection_id: str) -> RepoConnection:
        conn = await self.get_connection(connection_id)
        token = await self._read_vault_secret(conn.vault_secret_path)
        connector = self._connectors[str(conn.provider)]
        success, error = await connector.verify_connection(conn, token)
        conn.status = RepoStatus.CONNECTED if success else RepoStatus.AUTH_FAILED
        conn.last_verified_at = datetime.now(UTC)
        conn.error_message = error
        conn.updated_at = datetime.now(UTC)
        await self._upsert_connection(conn)
        return conn

    async def rotate_token(self, connection_id: str, token: str) -> RepoConnection:
        conn = await self.get_connection(connection_id)
        await self._write_vault_secret(conn.vault_secret_path, token)
        return await self.verify_connection(connection_id)

    async def verify_all(self, client_id: str) -> list[RepoConnection]:
        connections = await self.list_connections(client_id)
        results: list[RepoConnection] = []
        for conn in connections:
            results.append(await self.verify_connection(conn.connection_id))
        return results

    async def resolve_scan_target(
        self,
        connection_id: str,
        ref_override: Optional[str] = None,
        scan_mode: str = "full_repo",
        diff_base: Optional[str] = None,
        diff_head: Optional[str] = None,
    ) -> RepoScanTarget:
        conn = await self.get_connection(connection_id)
        if conn.status != RepoStatus.CONNECTED:
            raise RepoNotConnectedError(
                f"Repo {conn.repo_name} status is {conn.status}. Re-verify before scanning."
            )
        token = await self._read_vault_secret(conn.vault_secret_path)
        connector = self._connectors[str(conn.provider)]
        ref = ref_override or conn.default_branch
        head_sha = await connector.get_latest_commit(conn, token, ref)
        return RepoScanTarget(
            connection_id=connection_id,
            repo_url=conn.repo_url,
            repo_ref=head_sha,
            repo_auth_token=token,
            diff_base=diff_base,
            diff_head=diff_head or head_sha,
            include_patterns=["**/*"],
            exclude_patterns=conn.exclude_patterns,
            crown_jewel_paths=conn.crown_jewel_paths,
            is_crown_jewel=conn.is_crown_jewel,
            scan_mode="incremental" if diff_base else scan_mode,
        )

    async def resolve_multi_repo(self, request: MultiRepoScanRequest) -> list[RepoScanTarget]:
        if request.scan_all:
            connections = await self.list_connections(request.client_id)
            ids = [c.connection_id for c in connections if c.status == RepoStatus.CONNECTED]
        else:
            ids = request.connection_ids

        results = await asyncio.gather(
            *[
                self.resolve_scan_target(connection_id=cid, ref_override=request.ref_override)
                for cid in ids
            ],
            return_exceptions=True,
        )
        return [target for target in results if isinstance(target, RepoScanTarget)]

    async def clone_to_temp(self, connection_id: str, ref: str) -> str:
        conn = await self.get_connection(connection_id)
        token = await self._read_vault_secret(conn.vault_secret_path)
        connector = self._connectors[str(conn.provider)]
        tmpdir = tempfile.mkdtemp(prefix=f"unishield-{conn.repo_name}-")
        return await connector.clone_repo(conn, token, ref, tmpdir)

    async def get_connection(self, connection_id: str) -> RepoConnection:
        row = await self._postgres.fetchrow(
            "SELECT * FROM repo_connections WHERE connection_id = $1",
            connection_id,
        )
        if not row:
            raise KeyError(f"Connection not found: {connection_id}")
        return self._row_to_connection(row)

    async def list_connections(self, client_id: str) -> list[RepoConnection]:
        rows = await self._postgres.fetch(
            "SELECT * FROM repo_connections WHERE client_id = $1 ORDER BY registered_at DESC",
            client_id,
        )
        return [self._row_to_connection(row) for row in rows]

    async def update_connection(self, connection: RepoConnection) -> RepoConnection:
        connection.updated_at = datetime.now(UTC)
        await self._upsert_connection(connection)
        return connection

    async def delete_connection(self, connection_id: str) -> None:
        conn = await self.get_connection(connection_id)
        await self._vault.delete_secret(conn.vault_secret_path)
        await self._postgres.execute(
            "DELETE FROM repo_connections WHERE connection_id = $1",
            connection_id,
        )

    async def get_token(self, connection_id: str) -> str:
        conn = await self.get_connection(connection_id)
        return await self._read_vault_secret(conn.vault_secret_path)

    async def mark_scanned(self, connection_id: str, scan_id: str) -> None:
        await self._postgres.execute(
            """
            UPDATE repo_connections
            SET last_scanned_at = $2, last_scan_id = $3, updated_at = $2
            WHERE connection_id = $1
            """,
            connection_id,
            _pg_timestamp(datetime.now(UTC)),
            scan_id,
        )

    async def _upsert_connection(self, connection: RepoConnection) -> None:
        await self._postgres.execute(
            """
            INSERT INTO repo_connections (
                connection_id, client_id, provider, auth_method, repo_url, repo_owner,
                repo_name, default_branch, vault_secret_path, description, is_crown_jewel,
                crown_jewel_paths, exclude_patterns, include_languages, status,
                last_verified_at, last_scanned_at, last_scan_id, error_message,
                registered_at, registered_by, updated_at
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22
            )
            ON CONFLICT (connection_id) DO UPDATE SET
                default_branch = EXCLUDED.default_branch,
                description = EXCLUDED.description,
                is_crown_jewel = EXCLUDED.is_crown_jewel,
                crown_jewel_paths = EXCLUDED.crown_jewel_paths,
                exclude_patterns = EXCLUDED.exclude_patterns,
                include_languages = EXCLUDED.include_languages,
                status = EXCLUDED.status,
                last_verified_at = EXCLUDED.last_verified_at,
                last_scanned_at = EXCLUDED.last_scanned_at,
                last_scan_id = EXCLUDED.last_scan_id,
                error_message = EXCLUDED.error_message,
                updated_at = EXCLUDED.updated_at
            """,
            connection.connection_id,
            connection.client_id,
            str(connection.provider),
            str(connection.auth_method),
            connection.repo_url,
            connection.repo_owner,
            connection.repo_name,
            connection.default_branch,
            connection.vault_secret_path,
            connection.description,
            connection.is_crown_jewel,
            json.dumps(connection.crown_jewel_paths),
            json.dumps(connection.exclude_patterns),
            json.dumps(connection.include_languages),
            str(connection.status),
            _pg_timestamp(connection.last_verified_at),
            _pg_timestamp(connection.last_scanned_at),
            connection.last_scan_id,
            connection.error_message,
            _pg_timestamp(connection.registered_at),
            connection.registered_by,
            _pg_timestamp(connection.updated_at),
        )

    def _row_to_connection(self, row: dict[str, Any]) -> RepoConnection:
        return RepoConnection(
            connection_id=row["connection_id"],
            client_id=row["client_id"],
            provider=str(row["provider"]),
            auth_method=str(row["auth_method"]),
            repo_url=row["repo_url"],
            repo_owner=row["repo_owner"],
            repo_name=row["repo_name"],
            default_branch=row["default_branch"],
            vault_secret_path=row["vault_secret_path"],
            description=row.get("description"),
            is_crown_jewel=row["is_crown_jewel"],
            crown_jewel_paths=self._json_list(row.get("crown_jewel_paths")),
            exclude_patterns=self._json_list(row.get("exclude_patterns")),
            include_languages=self._json_list(row.get("include_languages")),
            status=RepoStatus(row["status"]),
            last_verified_at=_from_pg_timestamp(row.get("last_verified_at")),
            last_scanned_at=_from_pg_timestamp(row.get("last_scanned_at")),
            last_scan_id=row.get("last_scan_id"),
            error_message=row.get("error_message"),
            registered_at=_from_pg_timestamp(row["registered_at"]),
            registered_by=row["registered_by"],
            updated_at=_from_pg_timestamp(row.get("updated_at")),
        )

    @staticmethod
    def _json_list(value: Any) -> list:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return json.loads(value)
        return list(value)

    async def _write_vault_secret(self, path: str, token: str) -> None:
        await self._vault.write_secret(path, token)

    async def _read_vault_secret(self, path: str) -> str:
        return await self._vault.read_secret(path)
