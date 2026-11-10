"""db-migrate: runs ONCE before orders-api starts (an init container in Kubernetes).

Waits for Postgres, then creates the schema. Exits 0 on success, 1 on failure.
Run with:  python -m app.migrate
"""
import sys
import time

from app.db import connect

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id         SERIAL PRIMARY KEY,
    item       TEXT        NOT NULL,
    qty        INTEGER     NOT NULL CHECK (qty > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

for attempt in range(1, 31):
    try:
        with connect() as c:
            c.execute(SCHEMA)
        print(f"[db-migrate] schema ready (attempt {attempt})", flush=True)
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        print(f"[db-migrate] postgres not ready ({attempt}/30): {e.__class__.__name__}", flush=True)
        time.sleep(2)

print("[db-migrate] giving up after 30 attempts", flush=True)
sys.exit(1)
