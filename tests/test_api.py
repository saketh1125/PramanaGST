"""API smoke tests via FastAPI TestClient (no live server needed)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def _first_gstin() -> str:
    risks = client.get("/api/v1/risks").json()
    return risks[0]["gstin"]


def test_health():
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_ingest_metadata_only():
    r = client.post("/api/v1/ingest")
    assert r.status_code == 200
    meta = r.json()["metadata"]
    assert meta["accepted_total"] == 361
    assert "persisted" not in r.json()


def test_reconciliation_endpoint():
    r = client.get("/api/v1/reconciliation")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["totalClaims"] == 91
    assert len(body["items"]) == 91


def test_risks_sorted_with_bands():
    r = client.get("/api/v1/risks")
    assert r.status_code == 200
    scores = [v["score"] for v in r.json()]
    assert scores == sorted(scores, reverse=True)


def test_explain_returns_narrative():
    gstin = _first_gstin()
    r = client.get(f"/api/v1/risks/{gstin}/explain")
    assert r.status_code == 200
    assert "narrative" in r.json() and len(r.json()["narrative"]) > 40


def test_ego_graph_shape():
    gstin = _first_gstin()
    r = client.get(f"/api/v1/graph/ego/{gstin}")
    assert r.status_code == 200
    body = r.json()
    assert body["nodes"] and body["links"]
    node_ids = {n["id"] for n in body["nodes"]}
    for link in body["links"]:
        assert link["source"] in node_ids and link["target"] in node_ids


def test_unknown_vendor_404():
    assert client.get("/api/v1/risks/99NOPE0000X1Z9").status_code == 404
    assert client.get("/api/v1/reconciliation/99NOPE0000X1Z9").json()["summary"]["totalClaims"] == 0
