#!/usr/bin/env python3
"""Redis stream consumer workers for UniShield agents (Week 2)."""

import argparse
import asyncio
import signal
import sys

from agents.registry import AGENT_CLASSES, create_agent
from packages.shared_types.constants import AgentName


async def run_worker(agent_name: str, tenant_id: str = "meridian-financial") -> None:
    """Start a single agent Redis consumer loop."""
    if agent_name not in AGENT_CLASSES:
        raise SystemExit(f"Unknown agent: {agent_name}")
    agent = create_agent(agent_name, tenant_id)
    print(f"UniShield worker: {agent_name} listening on task stream (tenant={tenant_id})")
    await agent.run()


async def run_all_workers(tenant_id: str = "meridian-financial") -> None:
    """Start all specialist agents except orchestrator (optional separate process)."""
    names = [n.value for n in AgentName if n != AgentName.ORCHESTRATOR]
    tasks = [asyncio.create_task(run_worker(name, tenant_id)) for name in names]
    await asyncio.gather(*tasks)


def main() -> None:
    parser = argparse.ArgumentParser(description="UniShield agent Redis workers")
    parser.add_argument(
        "--agent",
        help="Run a single agent worker (default: all specialists)",
    )
    parser.add_argument(
        "--tenant",
        default="meridian-financial",
        help="Default tenant id for agent identity",
    )
    parser.add_argument(
        "--include-orchestrator",
        action="store_true",
        help="When running all workers, include orchestrator",
    )
    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, loop.stop)
    except NotImplementedError:
        pass

    if args.agent:
        loop.run_until_complete(run_worker(args.agent, args.tenant))
    else:
        if args.include_orchestrator:
            loop.run_until_complete(
                asyncio.gather(
                    run_all_workers(args.tenant),
                    run_worker(AgentName.ORCHESTRATOR, args.tenant),
                )
            )
        else:
            loop.run_until_complete(run_all_workers(args.tenant))


if __name__ == "__main__":
    main()
