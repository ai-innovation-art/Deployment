"""menu-api: serves the QuickBite menu.

Teaching hooks:
  * Reads Redis first (cache), falls back to the built-in list   -> service-to-service DNS
  * Returns pod + node name                                      -> see load balancing & scheduling
  * APP_VERSION baked at build time (1.0 / 1.1 / 1.2-broken)      -> rolling update & rollback
  * BROKEN=true makes /ready fail forever                         -> a rollout that never finishes
"""
import json
import os
import socket
import time

import redis
from fastapi import FastAPI, Response

VERSION = os.getenv("APP_VERSION", "dev")
BROKEN = os.getenv("BROKEN", "false").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "30"))

r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379,
                socket_timeout=1, socket_connect_timeout=1, decode_responses=True)

MENU = [
    {"id": 1, "name": "Masala Dosa", "price": 120},
    {"id": 2, "name": "Paneer Butter Masala", "price": 220},
    {"id": 3, "name": "Veg Biryani", "price": 180},
]
if VERSION != "1.0":  # the "new feature" shipped in 1.1
    MENU.append({"id": 4, "name": "Spicy Paneer Wrap (NEW in 1.1)", "price": 150})

app = FastAPI(title="menu-api")
STARTED = time.time()


def whoami():
    return {"version": VERSION, "pod": socket.gethostname(),
            "node": os.getenv("NODE_NAME", "not-in-k8s")}


@app.get("/health")
def health():
    # Liveness: "is the process alive?" Never check dependencies here.
    return {"status": "ok"}


@app.get("/ready")
def ready(resp: Response):
    # Readiness: "should I receive traffic right now?"
    if BROKEN:
        resp.status_code = 503
        return {"ready": False, "reason": "broken build: required config not found"}
    return {"ready": True}


@app.get("/version")
def version():
    return {**whoami(), "uptime_s": round(time.time() - STARTED)}


@app.get("/menu")
def menu():
    key = "menu:" + VERSION
    try:
        cached = r.get(key)
        if cached:
            return {"items": json.loads(cached), "source": "redis-cache", **whoami()}
        r.setex(key, CACHE_TTL, json.dumps(MENU))
        source = "built-in (cache filled)"
    except redis.RedisError:
        source = "built-in (redis unreachable!)"
    return {"items": MENU, "source": source, **whoami()}
