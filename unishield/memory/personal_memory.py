"""Personal memory client — per-agent private Redis state."""

from __future__ import annotations

import json
from typing import Optional

import redis.asyncio as aioredis

AGENT_ID = "scr"
DEFAULT_TTL = 86400


class PersonalMemoryClient:
    """Private Redis workspace for the SCR agent."""

    def __init__(self, redis: aioredis.Redis, agent_id: str = AGENT_ID) -> None:
        self._redis = redis
        self._agent_id = agent_id

    @property
    def client(self) -> aioredis.Redis:
        return self._redis

    def _key(self, scan_id: str, section: str) -> str:
        return f"personal:{self._agent_id}:{scan_id}:{section}"

    async def save_scan_progress(
        self,
        scan_id: str,
        total_batches: int,
        completed_batches: list[str],
        failed_batches: list[str],
        current_batch_id: str,
    ) -> None:
        key = self._key(scan_id, "progress")
        data = {
            "total_batches": total_batches,
            "completed_batches": completed_batches,
            "failed_batches": failed_batches,
            "current_batch_id": current_batch_id,
        }
        await self._redis.set(key, json.dumps(data), ex=DEFAULT_TTL)

    async def load_scan_progress(self, scan_id: str) -> Optional[dict]:
        raw = await self._redis.get(self._key(scan_id, "progress"))
        if raw is None:
            return None
        return json.loads(raw)

    async def append_findings(
        self,
        scan_id: str,
        batch_id: str,
        code_findings: list[dict],
        secret_findings: list[dict],
        dep_findings: list[dict],
    ) -> None:
        for category, findings in [
            ("code", code_findings),
            ("secrets", secret_findings),
            ("deps", dep_findings),
        ]:
            if not findings:
                continue
            key = self._key(scan_id, f"findings:{category}")
            for finding in findings:
                await self._redis.rpush(key, json.dumps(finding))
            await self._redis.expire(key, DEFAULT_TTL)

    async def load_all_findings(self, scan_id: str) -> dict:
        result: dict[str, list] = {"code": [], "secrets": [], "deps": []}
        for category in result:
            key = self._key(scan_id, f"findings:{category}")
            raw_items = await self._redis.lrange(key, 0, -1)
            result[category] = [json.loads(item) for item in raw_items]
        return result

    async def add_fingerprint(self, scan_id: str, fingerprint: str) -> None:
        key = self._key(scan_id, "fingerprints")
        await self._redis.sadd(key, fingerprint)
        await self._redis.expire(key, DEFAULT_TTL)

    async def fingerprint_exists(self, scan_id: str, fingerprint: str) -> bool:
        return bool(await self._redis.sismember(self._key(scan_id, "fingerprints"), fingerprint))

    async def save_file_scanned(self, scan_id: str, file_path: str) -> None:
        key = self._key(scan_id, "files_scanned")
        await self._redis.sadd(key, file_path)
        await self._redis.expire(key, DEFAULT_TTL)

    async def get_files_scanned(self, scan_id: str) -> set[str]:
        members = await self._redis.smembers(self._key(scan_id, "files_scanned"))
        return set(members)

    async def increment_token_budget(self, scan_id: str, tokens_used: int) -> int:
        key = self._key(scan_id, "token_budget")
        total = await self._redis.incrby(key, tokens_used)
        await self._redis.expire(key, DEFAULT_TTL)
        return int(total)

    async def save_rule_cache(self, scan_id: str, rules: dict) -> None:
        await self._redis.set(
            self._key(scan_id, "rule_cache"),
            json.dumps(rules),
            ex=DEFAULT_TTL,
        )

    async def load_rule_cache(self, scan_id: str) -> Optional[dict]:
        raw = await self._redis.get(self._key(scan_id, "rule_cache"))
        if raw is None:
            return None
        return json.loads(raw)

    async def save_file_list(self, scan_id: str, files: list[str]) -> None:
        await self._redis.set(
            self._key(scan_id, "file_list"),
            json.dumps(files),
            ex=DEFAULT_TTL,
        )

    async def load_file_list(self, scan_id: str) -> list[str]:
        raw = await self._redis.get(self._key(scan_id, "file_list"))
        if raw is None:
            return []
        return json.loads(raw)

    async def save_detection(self, scan_id: str, detection: dict) -> None:
        await self._redis.set(
            self._key(scan_id, "detection"),
            json.dumps(detection),
            ex=DEFAULT_TTL,
        )

    async def load_detection(self, scan_id: str) -> Optional[dict]:
        raw = await self._redis.get(self._key(scan_id, "detection"))
        if raw is None:
            return None
        return json.loads(raw)

    async def expire_all(self, scan_id: str, ttl_seconds: int = DEFAULT_TTL) -> None:
        pattern = f"personal:{self._agent_id}:{scan_id}:*"
        keys = [k async for k in self._redis.scan_iter(match=pattern)]
        if keys:
            pipe = self._redis.pipeline()
            for key in keys:
                pipe.expire(key, ttl_seconds)
            await pipe.execute()

    async def clear_all(self, scan_id: str) -> None:
        pattern = f"personal:{self._agent_id}:{scan_id}:*"
        keys = [k async for k in self._redis.scan_iter(match=pattern)]
        if keys:
            await self._redis.delete(*keys)

    async def get_control(self, scan_id: str, name: str) -> Optional[str]:
        return await self._redis.get(self._key(scan_id, f"control:{name}"))

    async def set_control(self, scan_id: str, name: str, value: str, ttl: int = 3600) -> None:
        await self._redis.set(self._key(scan_id, f"control:{name}"), value, ex=ttl)

    async def save_stage_config(self, scan_id: str, stage_instructions: dict, output_schema: str) -> None:
        await self._redis.set(
            self._key(scan_id, "config:stage_instructions"),
            json.dumps(stage_instructions),
            ex=DEFAULT_TTL,
        )
        await self._redis.set(
            self._key(scan_id, "config:output_schema"),
            output_schema,
            ex=DEFAULT_TTL,
        )

    async def load_stage_config(self, scan_id: str) -> tuple[dict, str]:
        raw_inst = await self._redis.get(self._key(scan_id, "config:stage_instructions"))
        raw_schema = await self._redis.get(self._key(scan_id, "config:output_schema"))
        instructions = json.loads(raw_inst) if raw_inst else {}
        schema = raw_schema or ""
        return instructions, schema

    async def save_heartbeat(self, scan_id: str, data: dict) -> None:
        await self._redis.set(self._key(scan_id, "heartbeat"), json.dumps(data), ex=DEFAULT_TTL)

    async def save_scan_started(self, scan_id: str) -> None:
        await self._redis.set(self._key(scan_id, "started"), "true", ex=DEFAULT_TTL)

    async def save_scan_completed(self, scan_id: str, latency_ms: int) -> None:
        await self._redis.set(
            self._key(scan_id, "completed"),
            json.dumps({"latency_ms": latency_ms}),
            ex=DEFAULT_TTL,
        )
