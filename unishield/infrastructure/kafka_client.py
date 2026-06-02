"""Kafka producer and consumer using aiokafka."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable, Optional

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import ConsumerStoppedError

from unishield.config.settings import settings

logger = logging.getLogger(__name__)

MessageHandler = Callable[[dict], Awaitable[None]]


class KafkaProducer:
    """Async Kafka producer with JSON serialization."""

    def __init__(self, bootstrap_servers: Optional[str] = None) -> None:
        self._bootstrap = bootstrap_servers or settings.kafka_bootstrap_servers
        self._producer: Optional[AIOKafkaProducer] = None
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await self._producer.start()
        self._started = True

    async def stop(self) -> None:
        if self._producer and self._started:
            await self._producer.stop()
            self._started = False
            self._producer = None

    async def publish(
        self,
        topic: str,
        payload: dict,
        key: Optional[str] = None,
    ) -> None:
        if not self._producer:
            raise RuntimeError("KafkaProducer not started")
        await self._producer.send_and_wait(topic, payload, key=key)


class KafkaConsumer:
    """Async Kafka consumer with reconnect logic."""

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> None:
        self._bootstrap = bootstrap_servers or settings.kafka_bootstrap_servers
        self._group_id = group_id or settings.kafka_consumer_group
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._running = False

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            self._consumer = None

    async def consume(
        self,
        topic: str,
        group_id: str,
        handler: MessageHandler,
    ) -> None:
        """Loop forever, calling handler for each message."""
        while self._running:
            try:
                self._consumer = AIOKafkaConsumer(
                    topic,
                    bootstrap_servers=self._bootstrap,
                    group_id=group_id,
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    enable_auto_commit=False,
                )
                await self._consumer.start()
                async for msg in self._consumer:
                    if not self._running:
                        break
                    try:
                        await handler(msg.value)
                        await self._consumer.commit()
                    except Exception:
                        logger.exception("Handler failed for message on %s", topic)
            except ConsumerStoppedError:
                logger.info("Consumer stopped for topic %s", topic)
                break
            except Exception:
                logger.exception("Consumer error on %s — reconnecting in 5s", topic)
                await asyncio.sleep(5)
            finally:
                if self._consumer:
                    try:
                        await self._consumer.stop()
                    except Exception:
                        pass
                    self._consumer = None


class KafkaClient:
    """Combined Kafka producer/consumer facade."""

    def __init__(self) -> None:
        self.producer = KafkaProducer()
        self.consumer = KafkaConsumer()

    async def start(self) -> None:
        await self.producer.start()
        await self.consumer.start()

    async def stop(self) -> None:
        await self.consumer.stop()
        await self.producer.stop()

    async def publish(
        self,
        topic: str,
        payload: dict,
        key: Optional[str] = None,
    ) -> None:
        await self.producer.publish(topic, payload, key=key)
