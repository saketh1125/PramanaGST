"""Phases 4/5/6 — prod security, health/readiness, request IDs.

Reloads backend.api.main under controlled env vars; other test modules
keep their own dev-mode app binding and are unaffected.
"""

import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import backend.api.config as _config_module
import backend.api.main as _main_module


def _reload_main():
    importlib.reload(_config_module)
    return importlib.reload(_main_module)


@pytest.fixture()
def prod_module(monkeypatch):
    monkeypatch.setenv("PRAMANAGST_ENV", "prod")
    monkeypatch.setenv("PRAMANAGST_API_KEY", "test-key-123")
    mod = _reload_main()
    yield mod
    for var in ("PRAMANAGST_ENV", "PRAMANAGST_API_KEY",
                "PRAMANAGST_DATA_DIR", "PRAMANAGST_USE_NEO4J", "NEO4J_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    _reload_main()


def test_prod_disables_docs(prod_module):
    r = TestClient(prod_module.app).get("/docs")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_dev_docs_enabled():
    r = TestClient(_main_module.app).get("/openapi.json")
    assert r.status_code == 200


def test_ingest_requires_key_in_prod(prod_module):
    c = TestClient(prod_module.app)
    r = c.post("/api/v1/ingest")
    assert r.status_code == 401
    body = r.json()
    assert body["contract_version"] == "1.0.0" and body["entity"] == "ERROR"
    assert body["error"]["code"] == "UNAUTHORIZED"
    r = c.post("/api/v1/ingest", headers={"X-API-Key": "test-key-123"})
    assert r.status_code == 200
    assert r.json()["metadata"]["accepted_total"] == 361


def test_reads_stay_public_in_prod(prod_module):
    c = TestClient(prod_module.app)
    assert c.get("/api/v1/health").status_code == 200
    assert c.get("/api/v1/risks").status_code == 200


def test_health_carries_version():
    body = TestClient(_main_module.app).get("/api/v1/health").json()
    assert body["status"] == "ok" and body["version"] == "0.1.0"


def test_ready_reports_dataset():
    body = TestClient(_main_module.app).get("/api/v1/ready").json()
    assert body["status"] == "ready" and body["checks"]["dataset"] is True


def test_ready_fails_on_missing_dataset(prod_module, tmp_path, monkeypatch):
    monkeypatch.setenv("PRAMANAGST_DATA_DIR", str(tmp_path))
    mod = _reload_main()
    r = TestClient(mod.app).get("/api/v1/ready")
    assert r.status_code == 503
    assert r.json()["status"] == "not_ready"
    assert r.json()["checks"]["dataset"] is False


def test_request_id_roundtrip():
    c = TestClient(_main_module.app)
    r = c.get("/api/v1/health")
    assert r.headers.get("X-Request-ID")
    r = c.get("/api/v1/health", headers={"X-Request-ID": "probe-123"})
    assert r.headers["X-Request-ID"] == "probe-123"


def test_neo4j_errors_are_sanitized(prod_module, monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("dial tcp [::1]:7687: SECRET-CREDS-LEAK")
    monkeypatch.setenv("PRAMANAGST_USE_NEO4J", "1")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-pw")
    mod = _reload_main()
    monkeypatch.setattr(mod, "project_from_neo4j", _boom)
    r = TestClient(mod.app).get("/api/v1/risks")
    assert r.status_code == 503
    body = r.json()
    assert body["error"] == {"code": "SERVICE_UNAVAILABLE", "message": "Neo4j unavailable"}
    assert "SECRET-CREDS-LEAK" not in r.text
