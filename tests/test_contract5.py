"""Contract-5 schema, model, and API compatibility tests."""

import importlib.util
import json
import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.api.main import app
from backend.api.models.contract5 import (
    ErrorResponse,
    GraphLink,
    GraphNode,
    GraphView,
    RiskSummary,
    VendorRiskView,
)

from fastapi.testclient import TestClient

client = TestClient(app)


def _summary():
    return RiskSummary(totalVendors=20, highRisk=4, mediumRisk=7, lowRisk=9, averageScore=31.42)


def _view():
    return VendorRiskView(
        gstin="29ABCDE1234F1Z5",
        legalName="Acme Traders Pvt Ltd",
        score=72.5,
        band="HIGH",
        reasons=["3 of 10 invoices have ITC claim mismatches"],
        invoicesIssued=10,
    )


def test_risksummary_serialization_defaults():
    s = _summary()
    assert s.contract_version == "1.0.0"
    assert s.entity == "RISK_SUMMARY"
    dumped = s.model_dump()
    assert dumped["contract_version"] == "1.0.0"
    assert dumped["entity"] == "RISK_SUMMARY"
    assert dumped["totalVendors"] == 20
    assert dumped["averageScore"] == 31.42
    schema = RiskSummary.model_json_schema()
    assert schema["entity"] == "RISK_SUMMARY"
    assert {"contract_version", "entity"} <= set(schema["properties"])


def test_vendorriskview_serialization():
    v = _view()
    dumped = v.model_dump(by_alias=True)
    assert dumped["legalName"] == "Acme Traders Pvt Ltd"
    assert dumped["invoicesIssued"] == 10
    assert "signals" not in dumped
    assert "legal_name" not in dumped
    schema = VendorRiskView.model_json_schema()
    assert schema["entity"] == "VENDOR_RISK_VIEW"
    assert set(schema["properties"]) == {"contract_version", "entity", "gstin", "legalName", "score", "band", "reasons", "invoicesIssued"}
    assert dumped["contract_version"] == "1.0.0"
    assert dumped["entity"] == "VENDOR_RISK_VIEW"


def test_graphnode_graphlink_graphview_serialization():
    n = GraphNode(id="Taxpayer:29ABCDE1234F1Z5", label="Taxpayer", legalName="Acme")
    dumped = n.model_dump(by_alias=True, exclude_none=True)
    assert dumped["legalName"] == "Acme"
    assert dumped["id"].startswith("Taxpayer:")
    link = GraphLink(source="a", target="b", type="SUPPLIED")
    assert link.model_dump()["type"] == "SUPPLIED"
    gv = GraphView(nodes=[n], links=[link])
    assert gv.contract_version == "1.0.0"
    assert gv.entity == "GRAPH_VIEW"
    out = gv.model_dump(by_alias=True)
    assert set(out) == {"contract_version", "entity", "nodes", "links"}
    assert out["nodes"][0]["label"] == "Taxpayer"
    schema = GraphView.model_json_schema()
    assert schema["entity"] == "GRAPH_VIEW"
    assert {"contract_version", "entity"} <= set(schema["properties"])


def test_graphview_validates_ego_payload():
    risks = client.get("/api/v1/risks").json()
    gstin = risks[0]["gstin"]
    body = client.get(f"/api/v1/graph/ego/{gstin}").json()
    view = GraphView.model_validate(body)
    assert view.contract_version == "1.0.0"
    assert view.entity == "GRAPH_VIEW"
    assert view.nodes and view.links


def test_error_response_model():
    e = ErrorResponse(error={"code": "TAXPAYER_NOT_FOUND", "message": "Taxpayer X not found"})
    dumped = e.model_dump()
    assert dumped == {
        "contract_version": "1.0.0",
        "entity": "ERROR",
        "error": {"code": "TAXPAYER_NOT_FOUND", "message": "Taxpayer X not found"},
    }


def test_graph_models_forbid_extra_attributes():
    with pytest.raises(ValidationError):
        GraphNode(id="n1", label="Invoice", supplierGstin="INTERNAL", totalValue="123")
    with pytest.raises(ValidationError):
        GraphLink(source="a", target="b", internalWeight=0.42)
    node_schema = GraphNode.model_json_schema()
    assert node_schema.get("additionalProperties") is False
    assert GraphLink.model_json_schema().get("additionalProperties") is False


def _build_contract():
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "generate_contract5.py"))
    spec = importlib.util.spec_from_file_location("generate_contract5", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main()
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "contracts", "contract_5.json"))
    with open(out, encoding="utf-8") as f:
        return json.load(f)


def test_contract_schema_build_definitions():
    contract = _build_contract()
    assert contract["title"] == "PramanaGST Contract-5: Dashboard View Models"
    assert contract["version"] == "1.0.0"
    assert {"RiskSummary", "VendorRiskView", "GraphNode", "GraphLink", "GraphView", "ErrorResponse"} <= set(contract["definitions"])
    for name, defn in contract["definitions"].items():
        if name in ("RiskSummary", "VendorRiskView", "GraphView", "ErrorResponse"):
            assert "entity" in defn
            assert {"contract_version", "entity"} <= set(defn["properties"])
        else:  # GraphNode / GraphLink: envelope carries metadata, no per-item metadata
            assert "contract_version" not in defn.get("properties", {})
            assert "entity" not in defn["properties"]


def test_schema_model_consistency():
    contract = _build_contract()
    models = {
        "RiskSummary": RiskSummary,
        "VendorRiskView": VendorRiskView,
        "GraphNode": GraphNode,
        "GraphLink": GraphLink,
        "GraphView": GraphView,
        "ErrorResponse": ErrorResponse,
    }
    for name, model in models.items():
        defn = contract["definitions"][name]
        model_schema = model.model_json_schema()
        assert set(defn["properties"]) == set(model_schema["properties"])
        assert set(defn.get("required", [])) == set(model_schema.get("required", []))

    vendor_props = contract["definitions"]["VendorRiskView"]["properties"]
    assert "legalName" in vendor_props
    assert "invoicesIssued" in vendor_props
    assert "signals" not in vendor_props
    node_props = contract["definitions"]["GraphNode"]["properties"]
    assert {"id", "label", "legalName", "invoiceNumber", "returnId"} <= set(node_props)
    assert "gstin" not in node_props
    assert contract["definitions"]["GraphNode"].get("additionalProperties") is False
    assert contract["definitions"]["GraphLink"].get("additionalProperties") is False
    link_props = contract["definitions"]["GraphLink"]["properties"]
    assert {"source", "target", "type"} <= set(link_props)
    summary_props = contract["definitions"]["RiskSummary"]["properties"]
    assert {"contract_version", "entity", "totalVendors", "highRisk", "mediumRisk", "lowRisk", "averageScore"} <= set(summary_props)
    view_props = contract["definitions"]["GraphView"]["properties"]
    assert {"contract_version", "entity", "nodes", "links"} <= set(view_props)
    error_props = contract["definitions"]["ErrorResponse"]["properties"]
    assert "error" in error_props


def test_api_risks_flattened_view():
    r = client.get("/api/v1/risks")
    assert r.status_code == 200
    items = r.json()
    assert items
    for it in items:
        assert {"contract_version", "entity", "gstin", "legalName", "score", "band", "reasons", "invoicesIssued"} <= set(it)
        assert it["contract_version"] == "1.0.0"
        assert it["entity"] == "VENDOR_RISK_VIEW"
        assert "signals" not in it
        assert isinstance(it["invoicesIssued"], int)


def test_api_risks_band_filter():
    items = client.get("/api/v1/risks?band=HIGH").json()
    assert all(v["band"] == "HIGH" for v in items)
    bad = client.get("/api/v1/risks?band=BOGUS")
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "VALIDATION_ERROR"


def test_api_risk_summary():
    r = client.get("/api/v1/risk-summary")
    assert r.status_code == 200
    body = r.json()
    assert body["contract_version"] == "1.0.0"
    assert body["entity"] == "RISK_SUMMARY"
    risks = client.get("/api/v1/risks").json()
    assert body["totalVendors"] == len(risks)
    assert body["highRisk"] + body["mediumRisk"] + body["lowRisk"] == body["totalVendors"]
    assert 0 <= body["averageScore"] <= 100


def test_api_explain_envelope():
    risks = client.get("/api/v1/risks").json()
    gstin = risks[0]["gstin"]
    body = client.get(f"/api/v1/risks/{gstin}/explain").json()
    assert body["contract_version"] == "1.0.0"
    assert body["entity"] == "AUDIT_NARRATIVE"
    assert body["gstin"] == gstin
    assert len(body["narrative"]) > 40


def test_api_ego_graph_view():
    risks = client.get("/api/v1/risks").json()
    gstin = risks[0]["gstin"]
    body = client.get(f"/api/v1/graph/ego/{gstin}").json()
    assert body["contract_version"] == "1.0.0"
    assert body["entity"] == "GRAPH_VIEW"
    assert body["nodes"] and body["links"]
    node_ids = {n["id"] for n in body["nodes"]}
    for link in body["links"]:
        assert link["source"] in node_ids and link["target"] in node_ids


def test_api_404_error_shape():
    r = client.get("/api/v1/risks/99NOPE0000X1Z9")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "VENDOR_NOT_FOUND"
    assert "message" in r.json()["error"]
    r2 = client.get("/api/v1/graph/ego/99NOPE0000X1Z9")
    assert r2.status_code == 404
    assert r2.json()["error"]["code"] == "TAXPAYER_NOT_FOUND"


def test_routing_404_uses_error_envelope():
    r = client.get("/api/v1/nonexistent")
    assert r.status_code == 404
    body = r.json()
    assert body["contract_version"] == "1.0.0"
    assert body["entity"] == "ERROR"
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "Route not found"


def test_ego_nodes_expose_only_contract_fields():
    risks = client.get("/api/v1/risks").json()
    gstin = risks[0]["gstin"]
    body = client.get(f"/api/v1/graph/ego/{gstin}").json()
    allowed_node = {"id", "label", "legalName", "invoiceNumber", "returnId"}
    allowed_link = {"source", "target", "type"}
    for n in body["nodes"]:
        assert set(n) <= allowed_node
    for l in body["links"]:
        assert set(l) <= allowed_link


def test_risk_summary_ignores_list_filters():
    summary = client.get("/api/v1/risk-summary").json()
    high_only = client.get("/api/v1/risks?band=HIGH").json()
    assert summary["highRisk"] == len(high_only)
    assert summary["totalVendors"] == len(client.get("/api/v1/risks").json())


def test_vendor_risk_view_is_projection_of_contract4_detail():
    risks = client.get("/api/v1/risks").json()
    gstin = risks[0]["gstin"]
    view = risks[0]
    detail = client.get(f"/api/v1/risks/{gstin}").json()
    assert view["gstin"] == detail["gstin"]
    assert view["score"] == detail["score"]
    assert view["band"] == detail["band"]
    assert view["invoicesIssued"] == detail["signals"]["invoicesIssued"]
    assert "signals" in detail and "signals" not in view


def test_api_422_error_shape():
    risks = client.get("/api/v1/risks").json()
    gstin = risks[0]["gstin"]
    r = client.get(f"/api/v1/graph/ego/{gstin}?depth=abc")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "message" in r.json()["error"]
