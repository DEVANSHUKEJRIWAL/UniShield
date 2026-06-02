"""SCR agent Kafka consumer entry point."""

from __future__ import annotations

import asyncio
import logging

from unishield.agents.scr.schemas.input_schema import SCRAgentInput, ScanMode, TriggerSource
from unishield.agents.scr.scr_agent import SCRAgent
from unishield.infrastructure.kafka_client import KafkaClient
from unishield.infrastructure.redis_client import RedisClient
from unishield.memory.personal_memory import PersonalMemoryClient
from unishield.memory.shared_memory import SharedMemoryClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_scan_request(payload: dict) -> None:
    redis = RedisClient.get_instance()
    personal = PersonalMemoryClient(redis.client)
    shared = SharedMemoryClient(redis.client)
    kafka = KafkaClient()

    agent = SCRAgent(personal, shared, kafka)
    scan_input = SCRAgentInput(
        request_id=payload.get("correlation_id", payload["workflow_id"]),
        client_id=payload["client_id"],
        triggered_by=TriggerSource.MANUAL,
        scan_mode=ScanMode.FULL_REPO,
        repo_url=payload.get("repo_url"),
        repo_ref=payload.get("repo_ref"),
        workflow_id=payload["workflow_id"],
    )
    await agent.run(scan_input)


async def main() -> None:
    redis = RedisClient.get_instance()
    await redis.connect()

    kafka = KafkaClient()
    await kafka.start()

    logger.info("SCR agent consumer starting on scr.scan.requests")
    await kafka.consumer.consume("scr.scan.requests", "unishield-scr-agent", handle_scan_request)


if __name__ == "__main__":
    asyncio.run(main())
