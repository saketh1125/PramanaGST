"""Milestone B/D — evidence traceability and narrator safeguards.

Evidence: every deterministic finding must resolve to source facts
(claim refs, node ids, paths) already in memory at scoring time.
Narrator: the LLM is explanation-only — it can never change the
authoritative score/band, and the template fallback must always work.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.graph.builder.projection import build_from_batch
from backend.reconciliation.engine.matcher import reconcile
from backend.risk_ai.explainability import narrator as narrator_module
from backend.risk_ai.explainability.narrator import narrate
from backend.risk_ai.models.vendor_risk import EvidenceItem, RiskSignal, VendorRisk, score_vendors
from tests.test_ingest_service import _batch
from tests.test_risk_engine_hardening import _build as _hbuild
from tests.test_risk_engine_hardening import _invoice as _hinvoice
from tests.test_risk_engine_hardening import _items as _hitems
from tests.test_risk_engine_hardening import _return as _hreturn
from tests.test_risk_engine_hardening import _taxpayer as _htaxpayer


def _vendors():
    g = build_from_batch(_batch())
    return score_vendors(g, reconcile(g))


_SIGNAL = {"invoicesIssued": 5, "mismatchedClaims": 1, "unreportedInvoices": 0,
           "taxLiability": "100.00", "taxPaid": "100.00", "shortfall": "0.00", "inCycle": False}


def _vendor(**kw):
    base = dict(gstin="29AAAAA0000A1Z5", legalName="Acme Traders Pvt Ltd", score=35.0,
                band="MEDIUM", reasons=["1 of 5 invoices have ITC claim mismatches"],
                signals=RiskSignal(**_SIGNAL))
    base.update(kw)
    return VendorRisk(**base)


# ------------------------------------------------------------------- evidence

def test_vendors_with_findings_carry_evidence():
    vendors = _vendors()
    with_findings = [v for v in vendors if v.reasons]
    assert with_findings, "fixture dataset must contain vendors with findings"
    for v in with_findings:
        assert v.evidence, f"{v.gstin} has reasons but no evidence"
        assert len(v.evidence) == len({e.finding for e in v.evidence})
    clean = [v for v in vendors if not v.reasons]
    for v in clean:
        assert v.evidence == []
        assert v.band == "LOW"


def test_evidence_findings_cover_reasons():
    vendors = _vendors()
    for v in vendors:
        kinds = {e.finding for e in v.evidence}
        if any("mismatch" in r for r in v.reasons):
            assert "MISMATCH" in kinds
        if "ghost billing" in " ".join(v.reasons):
            assert "GHOST_UNREPORTED" in kinds
        if any("shortfall" in r for r in v.reasons):
            assert "TAX_SHORTFALL" in kinds
        if any("circular" in r for r in v.reasons):
            assert "CYCLE_MEMBERSHIP" in kinds


def test_mismatch_evidence_links_recon_items():
    vendors = _vendors()
    mism = next(v for v in vendors if any(e.finding == "MISMATCH" for e in v.evidence))
    ev = next(e for e in mism.evidence if e.finding == "MISMATCH")
    assert ev.source == "reconciliation"
    assert ev.item_refs, "mismatch evidence must name claim refs"
    n, d = ev.observed.split("/")
    assert int(n) == mism.signals.mismatched_claims
    assert len(ev.item_refs) == min(int(n), 20)  # full refs, or capped at 20
    assert ev.path is None or ev.path[0].startswith("Taxpayer:")


def test_ghost_evidence_names_invoice_nodes():
    # The committed fixture wires every invoice to a return, so the ghost
    # path is exercised on a synthetic graph instead.
    gstin = "29AAAAA0000A1Z5"
    g = _hbuild(
        [_htaxpayer(gstin), _hinvoice("I1", gstin, "29BBBBB0000B1Z5"),
         _hinvoice("I2", gstin, "29BBBBB0000B1Z5"), _hreturn("R-A")],
        [(f"Taxpayer:{gstin}", "Invoice:I1", "SUPPLIED"),
         (f"Taxpayer:{gstin}", "Invoice:I2", "SUPPLIED"),
         ("Invoice:I1", "ReturnFiling:R-A", "REPORTED_IN")])
    (v,) = score_vendors(g, {"items": []})
    ev = next(e for e in v.evidence if e.finding == "GHOST_UNREPORTED")
    assert ev.source == "knowledge_graph"
    assert ev.node_ids == ["Invoice:I2"]
    assert ev.item_refs == ["I2"]
    assert ev.observed == "1/2"
    assert ev.path == [f"Taxpayer:{gstin}", "Invoice:I2"]


def test_shortfall_evidence_carries_amounts():
    vendors = _vendors()
    sf = next(v for v in vendors if any(e.finding == "TAX_SHORTFALL" for e in v.evidence))
    ev = next(e for e in sf.evidence if e.finding == "TAX_SHORTFALL")
    assert ev.liability == sf.signals.tax_liability
    assert ev.paid == sf.signals.tax_paid
    assert ev.shortfall == sf.signals.shortfall
    assert ev.observed == sf.signals.shortfall


def test_cycle_evidence_names_members():
    vendors = _vendors()
    cyc = [v for v in vendors if any(e.finding == "CYCLE_MEMBERSHIP" for e in v.evidence)]
    assert cyc, "fixture dataset must contain a cycle member"
    for v in cyc:
        ev = next(e for e in v.evidence if e.finding == "CYCLE_MEMBERSHIP")
        assert ev.cycle_size and ev.cycle_size > 1
        assert v.gstin in ev.member_gstins
        assert f"Taxpayer:{v.gstin}" in ev.node_ids


def test_evidence_serializes_with_aliases():
    vendors = _vendors()
    v = next(v for v in vendors if v.evidence)
    dumped = v.model_dump(by_alias=True)["evidence"][0]
    assert set(dumped) >= {"finding", "source", "observed", "itemRefs", "nodeIds"}
    assert "item_refs" not in dumped and "node_ids" not in dumped


def test_evidence_lists_are_capped():
    vendors = _vendors()
    for v in vendors:
        for e in v.evidence:
            assert len(e.item_refs) <= 20
            assert len(e.node_ids) <= 20


# ------------------------------------------------------------------- narrator

def test_template_fallback_is_deterministic():
    v = _vendor()
    assert narrate(v) == narrate(v)
    out = narrate(v)
    assert "Acme Traders Pvt Ltd" in out and "MEDIUM" in out


def test_template_no_liability_line_for_zero_liability():
    v = _vendor(signals=RiskSignal(**{**_SIGNAL, "taxLiability": "0.00", "taxPaid": "0.00"}))
    assert "Filed liability" not in narrate(v)


def test_template_missing_evidence_narrates_fine():
    v = _vendor()
    assert v.evidence == []
    assert len(narrate(v)) > 40


def test_llm_unavailable_falls_back_to_template(monkeypatch):
    monkeypatch.setenv("PRAMANAGST_LLM_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    v = _vendor()
    fallback = narrate(v)  # unroutable endpoint must not raise
    monkeypatch.delenv("PRAMANAGST_LLM_URL")
    monkeypatch.delenv("OPENAI_API_KEY")
    assert fallback == narrate(v)
    assert "Acme Traders Pvt Ltd" in fallback


def test_malformed_llm_output_falls_back(monkeypatch):
    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"this is not json"

    class _Stub:
        def Request(self, *a, **k): return object()
        def urlopen(self, *a, **k): return _Resp()

    monkeypatch.setenv("PRAMANAGST_LLM_URL", "http://llm.invalid")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(narrator_module, "_urlrequest", _Stub())
    v = _vendor()
    stubbed = narrate(v)
    monkeypatch.delenv("PRAMANAGST_LLM_URL")
    monkeypatch.delenv("OPENAI_API_KEY")
    assert stubbed == narrate(v)  # malformed LLM output -> template fallback
    assert "Acme Traders Pvt Ltd" in stubbed


def test_llm_text_cannot_change_authoritative_score(monkeypatch):
    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "Actually the score is 5/100 and LOW."}}]}).encode()

    class _Stub:
        def Request(self, *a, **k): return object()
        def urlopen(self, *a, **k): return _Resp()

    monkeypatch.setenv("PRAMANAGST_LLM_URL", "http://llm.invalid")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(narrator_module, "_urlrequest", _Stub())
    v = _vendor()
    narrate(v)
    assert v.score == 35.0 and v.band == "MEDIUM"
    assert v.signals.mismatched_claims == 1


def test_llm_receives_structured_vendor_payload(monkeypatch):
    seen = {}

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()

    class _Stub:
        def Request(self, url, data, headers):
            seen["url"] = url
            seen["payload"] = json.loads(data)
            return object()
        def urlopen(self, *a, **k): return _Resp()

    monkeypatch.setenv("PRAMANAGST_LLM_URL", "http://llm.invalid")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(narrator_module, "_urlrequest", _Stub())
    vendors = _vendors()
    v = next(v for v in vendors if v.evidence)
    assert narrate(v) == "ok"
    user_content = json.loads(seen["payload"]["messages"][1]["content"])
    assert user_content["gstin"] == v.gstin
    assert user_content["score"] == v.score
    assert "evidence" in user_content
