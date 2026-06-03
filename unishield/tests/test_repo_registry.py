"""Tests for repo registry and connectors."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unishield.connectors.repo_registry import RepoRegistry, _from_pg_timestamp, _pg_timestamp
from unishield.schemas.repo_schemas import (
    RepoAuthMethod,
    RepoConnectionCreate,
    RepoStatus,
    VCSProvider,
)


@pytest.fixture
def registry() -> RepoRegistry:
    postgres = MagicMock()
    postgres.execute = AsyncMock()
    postgres.fetch = AsyncMock(return_value=[])
    postgres.fetchrow = AsyncMock(return_value=None)
    vault = MagicMock()
    vault.write_secret = AsyncMock()
    vault.read_secret = AsyncMock(return_value="ghp_testtoken")
    vault.delete_secret = AsyncMock()
    reg = RepoRegistry(postgres, vault)
    reg.init_schema = AsyncMock()
    return reg


@pytest.mark.asyncio
async def test_register_github_repo_success(registry: RepoRegistry):
    payload = RepoConnectionCreate(
        client_id="meridian-financial",
        provider=VCSProvider.GITHUB,
        auth_method=RepoAuthMethod.PAT,
        repo_url="https://github.com/acme/payments",
        repo_owner="acme",
        repo_name="payments",
        registered_by="analyst-1",
    )
    with patch.object(
        registry._connectors["github"],
        "verify_connection",
        AsyncMock(return_value=(True, None)),
    ) as verify:
        conn = await registry.register(payload, "ghp_testtoken")
    verify.assert_awaited_once()
    registry._vault.write_secret.assert_awaited()
    assert conn.status == RepoStatus.CONNECTED
    registry._postgres.execute.assert_awaited()


@pytest.mark.asyncio
async def test_register_invalid_token(registry: RepoRegistry):
    payload = RepoConnectionCreate(
        client_id="meridian-financial",
        provider=VCSProvider.GITHUB,
        auth_method=RepoAuthMethod.PAT,
        repo_url="https://github.com/acme/payments",
        repo_owner="acme",
        repo_name="payments",
        registered_by="analyst-1",
    )
    with patch.object(
        registry._connectors["github"],
        "verify_connection",
        AsyncMock(return_value=(False, "Token is invalid or expired")),
    ):
        conn = await registry.register(payload, "bad-token")
    assert conn.status == RepoStatus.AUTH_FAILED
    registry._vault.write_secret.assert_awaited()


@pytest.mark.asyncio
async def test_resolve_scan_target_builds_scr_fields(registry: RepoRegistry):
    now = datetime.now(UTC)
    registry._postgres.fetchrow = AsyncMock(
        return_value={
            "connection_id": "conn-1",
            "client_id": "meridian-financial",
            "provider": "github",
            "auth_method": "pat",
            "repo_url": "https://github.com/acme/payments",
            "repo_owner": "acme",
            "repo_name": "payments",
            "default_branch": "main",
            "vault_secret_path": "secret/test",
            "description": None,
            "is_crown_jewel": True,
            "crown_jewel_paths": '["src/payments"]',
            "exclude_patterns": '["**/test/**"]',
            "include_languages": "[]",
            "status": "connected",
            "last_verified_at": now,
            "last_scanned_at": None,
            "last_scan_id": None,
            "error_message": None,
            "registered_at": now,
            "registered_by": "analyst-1",
            "updated_at": None,
        }
    )
    with patch.object(
        registry._connectors["github"],
        "get_latest_commit",
        AsyncMock(return_value="abc123"),
    ):
        target = await registry.resolve_scan_target("conn-1")
    assert target.repo_ref == "abc123"
    assert target.is_crown_jewel is True
    assert "src/payments" in target.crown_jewel_paths


@pytest.mark.asyncio
async def test_scan_all_repos_resolves_multiple(registry: RepoRegistry):
    now = datetime.now(UTC)
    row = {
        "connection_id": "conn-1",
        "client_id": "meridian-financial",
        "provider": "github",
        "auth_method": "pat",
        "repo_url": "https://github.com/acme/a",
        "repo_owner": "acme",
        "repo_name": "a",
        "default_branch": "main",
        "vault_secret_path": "secret/test",
        "description": None,
        "is_crown_jewel": False,
        "crown_jewel_paths": "[]",
        "exclude_patterns": "[]",
        "include_languages": "[]",
        "status": "connected",
        "last_verified_at": now,
        "last_scanned_at": None,
        "last_scan_id": None,
        "error_message": None,
        "registered_at": now,
        "registered_by": "analyst-1",
        "updated_at": None,
    }
    rows = [row, {**row, "connection_id": "conn-2", "repo_name": "b"}]
    registry._postgres.fetch = AsyncMock(return_value=rows)

    async def _fetchrow(query, connection_id):
        for item in rows:
            if item["connection_id"] == connection_id:
                return item
        return None

    registry._postgres.fetchrow = AsyncMock(side_effect=_fetchrow)
    with patch.object(
        registry._connectors["github"],
        "get_latest_commit",
        AsyncMock(return_value="sha"),
    ):
        from unishield.schemas.repo_schemas import MultiRepoScanRequest

        targets = await registry.resolve_multi_repo(
            MultiRepoScanRequest(
                client_id="meridian-financial",
                workflow_id="code-review-only",
                scan_all=True,
            )
        )
    assert len(targets) == 2


@pytest.mark.asyncio
async def test_token_never_in_db(registry: RepoRegistry):
    payload = RepoConnectionCreate(
        client_id="meridian-financial",
        provider=VCSProvider.GITHUB,
        auth_method=RepoAuthMethod.PAT,
        repo_url="https://github.com/acme/payments",
        repo_owner="acme",
        repo_name="payments",
        registered_by="analyst-1",
    )
    with patch.object(
        registry._connectors["github"],
        "verify_connection",
        AsyncMock(return_value=(True, None)),
    ):
        await registry.register(payload, "ghp_secret")
    args = registry._postgres.execute.await_args.args
    joined = " ".join(str(a) for a in args)
    assert "ghp_secret" not in joined


@pytest.mark.asyncio
async def test_incremental_mode_when_diff_provided(registry: RepoRegistry):
    now = datetime.now(UTC)
    registry._postgres.fetchrow = AsyncMock(
        return_value={
            "connection_id": "conn-1",
            "client_id": "meridian-financial",
            "provider": "github",
            "auth_method": "pat",
            "repo_url": "https://github.com/acme/payments",
            "repo_owner": "acme",
            "repo_name": "payments",
            "default_branch": "main",
            "vault_secret_path": "secret/test",
            "description": None,
            "is_crown_jewel": False,
            "crown_jewel_paths": "[]",
            "exclude_patterns": "[]",
            "include_languages": "[]",
            "status": "connected",
            "last_verified_at": now,
            "last_scanned_at": None,
            "last_scan_id": None,
            "error_message": None,
            "registered_at": now,
            "registered_by": "analyst-1",
            "updated_at": None,
        }
    )
    with patch.object(
        registry._connectors["github"],
        "get_latest_commit",
        AsyncMock(return_value="headsha"),
    ):
        target = await registry.resolve_scan_target(
            "conn-1",
            diff_base="basesha",
            diff_head="headsha",
        )
    assert target.scan_mode == "incremental"


def test_pg_timestamp_converts_aware_to_naive_utc():
    aware = datetime(2026, 6, 3, 21, 5, 30, tzinfo=UTC)
    naive = _pg_timestamp(aware)
    assert naive is not None
    assert naive.tzinfo is None
    assert naive.hour == 21


def test_from_pg_timestamp_adds_utc():
    naive = datetime(2026, 6, 3, 21, 5, 30)
    aware = _from_pg_timestamp(naive)
    assert aware is not None
    assert aware.tzinfo == UTC
