#!/usr/bin/env bash
# Fix login 401 — reset demo users and show status
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> UniShield login fix"
echo ""

# Ensure not using postgres accidentally
unset UNISHIELD_USE_POSTGRES 2>/dev/null || true

python3 << 'PYEOF'
import asyncio
from core.config import settings
from core.database import bootstrap_dev_data, SessionLocal
from core.seed import ensure_demo_users
from core.auth import verify_password
from sqlalchemy import select, func
from core.models import User

async def main():
    print(f"Database: {'SQLite' if settings.uses_sqlite else 'PostgreSQL'}")
    if settings.sqlite_path:
        print(f"SQLite file: {settings.sqlite_path}")
    await bootstrap_dev_data()
    async with SessionLocal() as db:
        n = await ensure_demo_users(db)
        print(f"Demo users synced: {n}")
        r = await db.execute(select(User).where(User.email == "analyst@meridian.com"))
        u = r.scalar_one_or_none()
        if u and verify_password("analyst123", u.password_hash):
            print("OK: analyst@meridian.com / analyst123")
        else:
            print("FAILED: could not verify analyst password")

asyncio.run(main())
PYEOF

echo ""
echo "Restart the API, then test:"
echo '  curl http://localhost:8000/api/v1/dev/status'
echo '  curl -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '"'"'{"email":"analyst@meridian.com","password":"analyst123"}'"'"
