"""Reconciliation engine tests — deterministic dataset expectations."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.graph.builder.projection import build_from_batch
from backend.reconciliation.engine.matcher import reconcile
from backend.reconciliation.engine.models import ReconReport
from tests.test_ingest_service import _batch


def _report() -> ReconReport:
    raw = reconcile(build_from_batch(_batch()))
    return ReconReport(summary=raw["summary"], items=raw["items"])


def test_summary_counts_consistent():
    r = _report()
    s = r.summary
    assert s.total_claims == 91
    assert s.matched + s.mismatched + s.unreported == s.total_claims
    assert s.match_rate > 80.0


def test_deterministic_dataset_outcomes():
    r = _report()
    assert r.summary.matched == 79
    assert r.summary.mismatched == 12


def test_every_item_carries_graph_evidence():
    for item in _report().items:
        assert len(item.evidence_path) == 4
        assert item.evidence_path[1].startswith("Invoice:")
        assert item.supplier_gstin in item.evidence_path[0]


def test_mismatch_variance_is_real_money():
    r = _report()
    mismatches = [i for i in r.items if i.status.value == "MISMATCHED"]
    assert mismatches
    assert all(abs(i.variance) > 1 for i in mismatches)
    # varianceTotal equals sum of per-item variances
    total = sum((i.variance for i in r.items), start=__import__("decimal").Decimal("0"))
    assert total == r.summary.variance_total


def test_recipient_scoping():
    from backend.graph.builder.projection import build_from_batch

    g = build_from_batch(_batch())
    some = next(n.split(":", 1)[1] for n, d in g.nodes(data=True) if d["label"] == "Taxpayer")
    scoped = reconcile(g, gstin=some)
    if scoped["summary"]["totalClaims"]:
        assert all(i["recipientGstin"] == some for i in scoped["items"])
