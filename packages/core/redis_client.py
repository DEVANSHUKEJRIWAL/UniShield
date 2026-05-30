"""Async Redis client and stream helpers."""

import json
from typing import Any

import redis.asyncio as aioredis

from packages.core.config import settings
from packages.shared_types.constants import RedisStream

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return shared Redis connection."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def publish_stream(stream: str, data: dict[str, Any], maxlen: int = 10000) -> str:
    """Append entry to Redis stream and return message ID."""
    client = await get_redis()
    payload = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in data.items()}
    return await client.xadd(stream, payload, maxlen=maxlen)


async def read_stream(
    stream: str,
    last_id: str = "0",
    count: int = 10,
    block_ms: int = 5000,
) -> list[tuple[str, dict[str, Any]]]:
    """Read entries from Redis stream."""
    client = await get_redis()
    results = await client.xread({stream: last_id}, count=count, block=block_ms)
    entries: list[tuple[str, dict[str, Any]]] = []
    for _stream_name, messages in results:
        for msg_id, fields in messages:
            parsed = {}
            for k, v in fields.items():
                try:
                    parsed[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    parsed[k] = v
            entries.append((msg_id, parsed))
    return entries


async def stream_length(stream: str) -> int:
    """Return stream length."""
    client = await get_redis()
    return await client.xlen(stream)


async def publish_finding(agent_name: str, finding: dict[str, Any]) -> str:
    """Publish agent finding to findings stream."""
    return await publish_stream(RedisStream.agent_findings(agent_name), finding)


async def publish_hitl_request(request: dict[str, Any]) -> str:
    """Publish HITL request to queue."""
    return await publish_stream(RedisStream.HITL_QUEUE, request)


async def publish_risk_score(score: dict[str, Any]) -> str:
    """Publish risk score update."""
    return await publish_stream(RedisStream.RISK_SCORES, score)


async def publish_audit(entry: dict[str, Any]) -> str:
    """Publish immutable audit log entry."""
    return await publish_stream(RedisStream.AUDIT_LOG, entry)


async def publish_event(event: dict[str, Any]) -> str:
    """Publish normalised event."""
    return await publish_stream(RedisStream.EVENTS_NORMALISED, event)
