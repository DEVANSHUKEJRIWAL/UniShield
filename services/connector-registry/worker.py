"""Connector ingest worker — polls Splunk/QRadar and publishes to Redis (Week 7)."""

import asyncio
import os
from typing import Any

from packages.core.config import settings
from packages.core.redis_client import publish_stream
from packages.shared_types.constants import RedisStream
from services.connector_registry.registry import registry


async def ingest_connector(name: str, tenant_id: str, config: dict[str, Any] | None = None) -> int:
    """Run single connector ingest and publish events."""
    try:
        connector = registry.get(name, tenant_id, config or {})
        events = await connector.ingest()
    except KeyError:
        return 0
    count = 0
    for event in events:
        event.setdefault("tenant_id", tenant_id)
        event.setdefault("source_type", name)
        event.setdefault("type", event.get("event_type", "siem_alert"))
        await publish_stream(RedisStream.events_raw(name), event)
        await publish_stream(RedisStream.EVENTS_NORMALISED, event)
        count += 1
    return count


async def run_ingest_cycle(tenant_id: str = "meridian-financial") -> dict[str, Any]:
    """Poll Splunk and QRadar connectors once."""
    splunk_config = {
        "url": settings.splunk_url,
        "token": settings.splunk_token,
    }
    qradar_config = dict(os.environ)
    results: dict[str, int] = {}
    for name, cfg in [("splunk", splunk_config), ("qradar", qradar_config)]:
        count = await ingest_connector(name, tenant_id, cfg)
        results[name] = count
    return {"tenant_id": tenant_id, "ingested": results}


async def run_connector_worker(
    tenant_id: str = "meridian-financial",
    interval_seconds: int = 60,
) -> None:
    """Background loop for connector ingest."""
    while True:
        try:
            summary = await run_ingest_cycle(tenant_id)
            for name, count in summary.get("ingested", {}).items():
                if count:
                    print(f"connector-worker: ingested {count} events from {name}")
        except Exception as exc:
            print(f"connector-worker error: {exc}")
        await asyncio.sleep(interval_seconds)


def main() -> None:
    tenant = os.getenv("UNISHIELD_TENANT_ID", "meridian-financial")
    interval = int(os.getenv("CONNECTOR_POLL_INTERVAL", "60"))
    asyncio.run(run_connector_worker(tenant, interval))


if __name__ == "__main__":
    main()
