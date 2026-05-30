#!/usr/bin/env bash
# Seed local development with mock clients, users, alerts, findings, cases
set -euo pipefail

cd "$(dirname "$0")/.."

export UNISHIELD_USE_SQLITE="${UNISHIELD_USE_SQLITE:-1}"

echo "==> Seeding UniShield database (${UNISHIELD_USE_SQLITE:+SQLite} mode)..."

python3 << 'PYEOF'
import asyncio
import os

os.environ.setdefault("UNISHIELD_USE_SQLITE", "1")

from packages.core.database import bootstrap_dev_data, SessionLocal
from packages.core.seed import seed_if_empty


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
