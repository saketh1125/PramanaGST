"""Risk AI tests — scoring bands, cycle detection, narration."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.graph.builder.projection import build_from_batch
from backend.reconciliation.engine.matcher import reconcile
from backend.risk_ai.explainability.narrator import narrate
from backend.risk_ai.models.vendor_risk import score_vendors
from tests.test_ingest_service import _batch


def _vendors():
    g = build_from_batch(_batch())
    return score_vendors(g, reconcile(g))


def test_all_issuing_vendors_scored():
    vendors = _vendors()
    assert len(vendors) == 20
    assert all(0 <= v.score <= 100 for v in vendors)
    assert all(v.band in ("HIGH", "MEDIUM", "LOW") for v in vendors)


def test_scores_sorted_descending():
    scores = [v.score for v in _vendors()]
    assert scores == sorted(scores, reverse=True)


def test_cycles_detected():
    vendors = _vendors()
    assert any(v.signals.in_cycle for v in vendors)


def test_reasons_backed_by_signals():
    for v in _vendors():
        if v.signals.mismatched_claims:
            assert any("mismatch" in r.lower() for r in v.reasons)
        else:
            assert not any("mismatch" in r.lower() for r in v.reasons)


def test_narration_is_readable_and_factual():
    top = max(_vendors(), key=lambda v: v.score)
    text = narrate(top)
    assert top.gstin in text and top.legal_name in text
    assert f"score {top.score}/100" in text
    for reason in top.reasons:
        assert reason.split(" ")[0] in text or reason in text


def test_narrator_template_when_no_llm_env(monkeypatch):
    monkeypatch.delenv("PRAMANAGST_LLM_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    text = narrate(_vendors()[0])
    assert "carries" in text
