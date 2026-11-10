"""orders-api: accepts orders, stores them in Postgres, publishes an event to Redis.

Request path: web (nginx) -> orders-api -> postgres (write) -> redis list 'orders:events' -> notifier
"""
import json
import os
import socket

import redis
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from app.db import connect

VERSION = os.getenv("APP_VERSION", "dev")
r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379,
                socket_timeout=1, socket_connect_timeout=1, decode_responses=True)
app = FastAPI(title="orders-api")


class OrderIn(BaseModel):
    item: str = Field(min_length=1, max_length=100)
    qty: int = Field(default=1, gt=0, le=20)


def whoami():
    return {"version": VERSION, "pod": socket.gethostname(),
            "node": os.getenv("NODE_NAME", "not-in-k8s")}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(resp: Response):
    # orders-api is useless without its database, so readiness checks it.
    try:
        with connect() as c:
            c.execute("SELECT 1")
        return {"ready": True}
    except Exception as e:  # noqa: BLE001
        resp.status_code = 503
        return {"ready": False, "reason": f"db: {e.__class__.__name__}"}


@app.post("/orders", status_code=201)
def create_order(o: OrderIn):
    try:
        with connect() as c:
            row = c.execute(
                "INSERT INTO orders (item, qty) VALUES (%s, %s) RETURNING id, created_at",
                (o.item, o.qty)).fetchone()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"database unavailable: {e.__class__.__name__}")
    event = {"order_id": row[0], "item": o.item, "qty": o.qty}
    try:
        r.lpush("orders:events", json.dumps(event))
        queued = True
    except redis.RedisError:
        queued = False  # the order is saved; the notification is best-effort
    return {**event, "created_at": row[1].isoformat(), "event_queued": queued, **whoami()}


@app.get("/orders")
def list_orders():
    try:
        with connect() as c:
            rows = c.execute(
                "SELECT id, item, qty, created_at FROM orders ORDER BY id DESC LIMIT 10").fetchall()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"database unavailable: {e.__class__.__name__}")
    return {"orders": [{"id": i, "item": it, "qty": q, "created_at": t.isoformat()}
                       for i, it, q, t in rows], **whoami()}
