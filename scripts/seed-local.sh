#!/usr/bin/env bash
# Seed local development with mock clients, users, alerts, findings, cases
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Seeding UniShield database (SQLite)..."

python3 << 'PYEOF'
import asyncio

from core.database import bootstrap_dev_data, SessionLocal
from core.seed import seed_if_empty


async def main() -> None:
    await bootstrap_dev_data()
    async with SessionLocal() as db:
        if await seed_if_empty(db):
            print("Seed complete (new data).")
        else:
            print("Seed skipped — users already exist.")


asyncio.run(main())
PYEOF

echo "==> Done. Login: analyst@meridian.com / analyst123"
