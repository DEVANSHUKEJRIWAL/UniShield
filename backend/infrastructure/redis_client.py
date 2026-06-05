"""Redis connection pool — singleton with async context manager support."""

from __future__ import annotations

from typing import Optional

import redis.asyncio as aioredis

from backend.config.settings import settings


class RedisClient:
    """Singleton Redis client with connection pooling."""

    _instance: Optional["RedisClient"] = None

    def __init__(self) -> None:
        self._pool: Optional[aioredis.ConnectionPool] = None
        self._client: Optional[aioredis.Redis] = None

    @classmethod
    def get_instance(cls) -> "RedisClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def connect(self) -> None:
        if self._client is not None:
            return
        self._pool = aioredis.ConnectionPool(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password or None,
            max_connections=settings.redis_max_connections,
            decode_responses=True,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        self._client = aioredis.Redis(connection_pool=self._pool)

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._pool is not None:
            await self._pool.disconnect()
            self._pool = None

    @property
    def client(self) -> aioredis.Redis:
        if self._client is None:
            raise RuntimeError("RedisClient not connected — call connect() first")
        return self._client

    async def ping(self) -> bool:
        return bool(await self.client.ping())

    async def __aenter__(self) -> "RedisClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.disconnect()


def get_redis() -> aioredis.Redis:
    """Return the underlying Redis client from the singleton."""
    return RedisClient.get_instance().client
