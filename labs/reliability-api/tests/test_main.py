import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_index():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "reliability-api"
    assert data["version"] == "0.1.0"
    assert "uptime_seconds" in data

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_ready():
    response = client.get("/ready")
    # Status code is 200 (if READY_DELAY is 0 default in tests) or 503
    assert response.status_code in (200, 503)

def test_work():
    response = client.get("/work?ms=10")
    assert response.status_code == 200
    data = response.json()
    assert "worked_ms" in data
    assert data["worked_ms"] >= 9.0

def test_leak():
    response = client.get("/leak?mb=5")
    assert response.status_code == 200
    data = response.json()
    assert data["allocated_now_mb"] == 5
    assert data["total_held_mb"] >= 5

def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text
