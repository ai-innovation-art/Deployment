import os
import time
import logging
from fastapi import FastAPI, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
READY_DELAY = float(os.getenv("READY_DELAY_SECONDS", "0"))
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("reliability-api")

REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["path", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["path"])

app = FastAPI(title="reliability-api", version="0.1.0")
STARTED = time.monotonic()
_allocated_memory = []

@app.get("/")
def index():
    return {
        "service": "reliability-api",
        "version": "0.1.0",
        "uptime_seconds": round(time.monotonic() - STARTED, 2),
        "ready_delay_seconds": READY_DELAY
    }

@app.get("/health")
def health():
    """Liveness probe: verifies that the process is alive and responsive."""
    return {"status": "ok"}

@app.get("/ready")
def ready(response: Response):
    """Readiness probe: returns 503 during startup warm-up, 200 when ready."""
    elapsed = time.monotonic() - STARTED
    if elapsed < READY_DELAY:
        response.status_code = 503
        return {
            "ready": False,
            "warming_up_seconds_remaining": round(READY_DELAY - elapsed, 2)
        }
    return {"ready": True}

@app.get("/work")
def work(ms: int = 50):
    """CPU-bound load generator: burns CPU in a tight loop for 'ms' milliseconds."""
    start = time.perf_counter()
    while (time.perf_counter() - start) * 1000 < ms:
        pass  # burn CPU deliberately
    elapsed = time.perf_counter() - start
    LATENCY.labels("/work").observe(elapsed)
    REQUESTS.labels("/work", "200").inc()
    return {"worked_ms": round(elapsed * 1000, 1)}

@app.get("/leak")
def leak(mb: int = 50):
    """Memory allocation test: allocates 'mb' megabytes to test cgroup memory limits & OOMKill."""
    # Allocate byte chunks and keep them referenced
    chunk = bytearray(mb * 1024 * 1024)
    _allocated_memory.append(chunk)
    total_allocated_mb = len(_allocated_memory) * mb
    log.info(f"Allocated {mb} MB. Total held: {total_allocated_mb} MB")
    return {
        "allocated_now_mb": mb,
        "total_held_mb": total_allocated_mb
    }

@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
