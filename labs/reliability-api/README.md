# reliability-api

The canonical test service for the DevOps & Kubernetes learning journey.

## Endpoints
- `GET /` — Service info and uptime
- `GET /health` — Liveness probe (always 200 OK)
- `GET /ready` — Readiness probe (503 while warming up, 200 when ready)
- `GET /work?ms=50` — CPU burner loop (used for HPA and load tests)
- `GET /leak?mb=50` — Memory allocation test (used for cgroup memory limit / OOMKill experiments)
- `GET /metrics` — Prometheus metrics (request counters and latency histograms)

## Quick Start (Local Python)
```bash
python -m venv .venv
source .venv/bin/activate    # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
pytest -v tests/
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Quick Start (Docker)
```bash
docker build -t reliability-api:0.1.0 .
docker run --rm -d --name reliability-api -p 8000:8000 -e READY_DELAY_SECONDS=10 reliability-api:0.1.0
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl "http://localhost:8000/work?ms=50"
curl http://localhost:8000/metrics
docker stop reliability-api
```
