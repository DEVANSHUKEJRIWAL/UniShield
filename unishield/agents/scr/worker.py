"""SCR worker — Kafka consumer invoking SCRRunner."""

from __future__ import annotations

import asyncio
import json
import logging

from openclaw_sdk.core.config import ClientConfig

from unishield.agents.scr.schemas.input_schema import SCRAgentInput, ScanMode, TriggerSource
from unishield.agents.scr.scr_runner import SCRRunner
from unishield.config.settings import settings
from unishield.infrastructure.kafka_client import KafkaConsumer, KafkaProducer
from unishield.infrastructure.model_router import ModelRouter
from unishield.infrastructure.redis_client import RedisClient
from unishield.memory.personal_memory import PersonalMemoryClient
from unishield.memory.shared_memory import SharedMemoryClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_message(payload: dict) -> None:
    redis = RedisClient.get_instance()
    personal = PersonalMemoryClient(redis.client)
    shared = SharedMemoryClient(redis.client)
    kafka = KafkaProducer()
    await kafka.start()

    config = ClientConfig(
        gateway_ws_url=settings.openclaw_gateway_ws_url,
        api_key=settings.openclaw_api_key,
        mock_mode=settings.openclaw_mock_mode,
    )
    runner = SCRRunner(config, shared, personal, kafka, settings, ModelRouter(settings))
    scan_input = SCRAgentInput(
        request_id=payload.get("request_id", payload["workflow_id"]),
        client_id=payload["client_id"],
        workflow_id=payload["workflow_id"],
        triggered_by=TriggerSource.MANUAL,
        scan_mode=ScanMode.FULL_REPO,
        repo_url=payload.get("repo_url"),
        repo_ref=payload.get("repo_ref"),
        file_paths=payload.get("file_paths", []),
    )
    await runner.run(scan_input)
    await kafka.stop()


async def main() -> None:
    redis = RedisClient.get_instance()
    await redis.connect()
    consumer = KafkaConsumer()
    await consumer.start()
    logger.info("SCR worker listening on agent.execute.scr")
    await consumer.consume("agent.execute.scr", "unishield-scr-worker", handle_message)


if __name__ == "__main__":
    asyncio.run(main())
