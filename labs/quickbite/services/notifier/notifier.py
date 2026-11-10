"""notifier: a background worker. It has no HTTP port and no Service.

Blocks on the Redis list 'orders:events' and "sends" a notification for each order.
"""
import json
import os
import socket
import time

import redis

r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, decode_responses=True)
me = socket.gethostname() + "@" + os.getenv("NODE_NAME", "not-in-k8s")
print(f"[notifier {me}] started, waiting for orders...", flush=True)

while True:
    try:
        msg = r.brpop("orders:events", timeout=5)
        if msg:
            e = json.loads(msg[1])
            print(f"[notifier {me}] SMS sent: order #{e['order_id']} "
                  f"({e['qty']} x {e['item']}) confirmed", flush=True)
    except redis.RedisError as err:
        print(f"[notifier {me}] redis unavailable ({err.__class__.__name__}), retry in 3s", flush=True)
        time.sleep(3)
