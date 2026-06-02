"""PostgreSQL async client using asyncpg."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

import asyncpg

from unishield.config.settings import settings

WORKFLOW_OUTPUTS_DDL = """
CREATE TABLE IF NOT EXISTS workflow_outputs (
    id              SERIAL PRIMARY KEY,
    workflow_id     VARCHAR(100) UNIQUE NOT NULL,
    client_id       VARCHAR(100) NOT NULL,
    snapshot        JSONB NOT NULL,
    checksum        VARCHAR(64) NOT NULL,
    completed_at    TIMESTAMP NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workflow_outputs_client
    ON workflow_outputs(client_id);

CREATE INDEX IF NOT EXISTS idx_workflow_outputs_completed
    ON workflow_outputs(completed_at);
"""


class PostgresClient:
    """Async PostgreSQL connection pool."""

    def __init__(self, dsn: Optional[str] = None) -> None:
        self._dsn = dsn or settings.postgres_dsn
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        if self._pool is not None:
            return
        self._pool = await asyncpg.create_pool(
            self._dsn,
            min_size=settings.postgres_min_pool,
            max_size=settings.postgres_max_pool,
        )

    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("PostgresClient not connected")
        return self._pool

    async def execute(self, query: str, *args: Any) -> str:
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def fetchrow(self, query: str, *args: Any) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[asyncpg.Connection]:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    async def init_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(WORKFLOW_OUTPUTS_DDL)

    async def __aenter__(self) -> "PostgresClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.disconnect()
