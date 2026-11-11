"""FastAPI smoke and optional integration tests."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"


def test_models_active(client: TestClient) -> None:
    r = client.get("/api/v1/models/active")
    assert r.status_code == 200
    data = r.json()
    assert "plate_appearance" in data
    assert "runs" in data


def test_models_evaluations_endpoint(client: TestClient) -> None:
    r = client.get("/api/v1/models/evaluations/latest")
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert "evaluations" in r.json()


@pytest.mark.integration
def test_status_with_database(client: TestClient) -> None:
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    r = client.get("/api/v1/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("database") == "ok"
    assert "plate_appearances" in body
