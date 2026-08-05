# tests/test_health.py
# Author: Suresh D R | AI Product Developer & Technology Mentor

from fastapi.testclient import TestClient


def test_health_endpoint_returns_status_field():
    from fastapi import FastAPI

    from src.api.routes.health import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "checks" in body
