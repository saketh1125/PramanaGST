"""Contract-4 schema and model tests."""

import importlib.util
import json
import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.risk_ai.models.contract4 import AuditNarrativeResponse
from backend.risk_ai.models.vendor_risk import RiskSignal, VendorRisk

_SIGNAL = {
    "invoicesIssued": 10,
    "mismatchedClaims": 3,
    "unreportedInvoices": 2,
    "taxLiability": "50000.00",
    "taxPaid": "35000.00",
    "shortfall": "15000.00",
    "inCycle": False,
}


def _vendor(**kw):
    base = dict(
        gstin="29ABCDE1234F1Z5",
        legalName="Acme Traders Pvt Ltd",
        score=72.5,
        band="HIGH",
        reasons=["3 of 10 invoices have ITC claim mismatches"],
        signals=RiskSignal(**_SIGNAL),
    )
    base.update(kw)
    return VendorRisk(**base)


def test_risksignal_serialization_aliases():
    s = RiskSignal(**_SIGNAL)
    dumped = s.model_dump(by_alias=True)
    assert dumped == _SIGNAL
    assert dumped["invoicesIssued"] == 10
    assert dumped["inCycle"] is False
    assert "invoices_issued" not in dumped


def test_vendorrisk_serialization_by_alias_contract_keys():
    v = _vendor()
    dumped = v.model_dump(by_alias=True)
    assert set(dumped) == {"gstin", "legalName", "score", "band", "reasons", "signals"}
    assert dumped["legalName"] == "Acme Traders Pvt Ltd"
    assert set(dumped["signals"]) == set(_SIGNAL)
    schema = VendorRisk.model_json_schema()
    assert schema["entity"] == "VENDOR_RISK"
    assert schema["contract_version"] == "1.0.0"


def test_score_bounds():
    with pytest.raises(ValidationError):
        _vendor(score=100.01)
    with pytest.raises(ValidationError):
        _vendor(score=-0.01)
    assert _vendor(score=0).score == 0
    assert _vendor(score=100).score == 100


def test_band_is_string():
    assert isinstance(_vendor().band, str)
    assert _vendor(band="LOW").band == "LOW"


def test_required_fields_validation():
    with pytest.raises(ValidationError):
        VendorRisk(legalName="x", score=10, band="LOW", signals=RiskSignal(**_SIGNAL))
    with pytest.raises(ValidationError):
        VendorRisk(gstin="g", score=10, band="LOW", signals=RiskSignal(**_SIGNAL))
    with pytest.raises(ValidationError):
        VendorRisk(gstin="g", legalName="x", band="LOW", signals=RiskSignal(**_SIGNAL))
    with pytest.raises(ValidationError):
        VendorRisk(gstin="g", legalName="x", score=10, signals=RiskSignal(**_SIGNAL))
    with pytest.raises(ValidationError):
        VendorRisk(gstin="g", legalName="x", score=10, band="LOW")
    with pytest.raises(ValidationError):
        RiskSignal(**{k: v for k, v in _SIGNAL.items() if k != "invoicesIssued"})


def test_audit_narrative_response_serialization():
    r = AuditNarrativeResponse(gstin="29ABCDE1234F1Z5", narrative="Vendor looks risky.")
    assert r.contract_version == "1.0.0"
    assert r.entity == "AUDIT_NARRATIVE"
    dumped = r.model_dump()
    assert dumped["contract_version"] == "1.0.0"
    assert dumped["entity"] == "AUDIT_NARRATIVE"
    assert dumped["gstin"] == "29ABCDE1234F1Z5"
    assert dumped["narrative"] == "Vendor looks risky."
    schema = AuditNarrativeResponse.model_json_schema()
    assert schema["entity"] == "AUDIT_NARRATIVE"
    assert schema["contract_version"] == "1.0.0"


def _build_contract():
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "generate_contract4.py"))
    spec = importlib.util.spec_from_file_location("generate_contract4", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main()
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "contracts", "contract_4.json"))
    with open(out, encoding="utf-8") as f:
        return json.load(f)


def test_contract_schema_build_definitions():
    contract = _build_contract()
    assert contract["title"] == "PramanaGST Contract-4: Risk Intelligence Interface"
    assert contract["version"] == "1.0.0"
    assert set(contract["definitions"]) == {"RiskSignal", "VendorRisk", "AuditNarrativeResponse"}
    for name, defn in contract["definitions"].items():
        assert "contract_version" in defn and defn["contract_version"] == "1.0.0"
        assert "entity" in defn


def test_schema_model_consistency():
    contract = _build_contract()
    models = {"RiskSignal": RiskSignal, "VendorRisk": VendorRisk, "AuditNarrativeResponse": AuditNarrativeResponse}
    for name, model in models.items():
        defn = contract["definitions"][name]
        model_schema = model.model_json_schema()
        assert set(defn["properties"]) == set(model_schema["properties"])
        assert set(defn.get("required", [])) == set(model_schema.get("required", []))

    risksignal_props = contract["definitions"]["RiskSignal"]["properties"]
    for alias in ("invoicesIssued", "mismatchedClaims", "unreportedInvoices", "taxLiability", "taxPaid", "shortfall", "inCycle"):
        assert alias in risksignal_props
    vendor_props = contract["definitions"]["VendorRisk"]["properties"]
    assert "legalName" in vendor_props
    assert {"gstin", "legalName", "score", "band", "signals"} <= set(vendor_props)
    narrative_props = contract["definitions"]["AuditNarrativeResponse"]["properties"]
    assert {"contract_version", "entity", "gstin", "narrative"} <= set(narrative_props)
    assert set(contract["definitions"]["AuditNarrativeResponse"]["required"]) == {"gstin", "narrative"}
