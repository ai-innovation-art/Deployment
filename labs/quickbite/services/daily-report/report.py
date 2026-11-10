"""daily-report: a batch job. It runs, prints a sales report and EXITS (Job / CronJob)."""
import os
import sys

import psycopg

try:
    with psycopg.connect(host=os.getenv("DB_HOST", "postgres"),
                         dbname=os.getenv("DB_NAME", "quickbite"),
                         user=os.getenv("DB_USER", "quickbite"),
                         password=os.getenv("DB_PASSWORD", "quickbite"),
                         connect_timeout=3) as c:
        rows = c.execute("SELECT item, SUM(qty), COUNT(*) FROM orders "
                         "GROUP BY item ORDER BY 2 DESC").fetchall()
except Exception as e:  # noqa: BLE001
    print(f"[daily-report] FAILED: {e}", flush=True)
    sys.exit(1)

print("=========== QuickBite sales report ===========")
print(f"{'item':35} {'units':>6} {'orders':>7}")
for item, units, n in rows:
    print(f"{item:35} {units:>6} {n:>7}")
print(f"TOTAL orders: {sum(r[2] for r in rows)}")
print("==============================================")
