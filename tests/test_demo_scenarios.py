"""Phase 9 — labelled synthetic demo dataset regression test.

The demo_scenarios dataset is SYNTHETIC (see its README). It pins the
controlled risk outcomes the dashboard demo relies on: one clean vendor,
single-signal vendors, circular pairs, and one multi-signal HIGH vendor.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.graph.builder.projection import build_from_batch
from backend.ingestion.ingest_service import IngestService
from backend.reconciliation.engine.matcher import reconcile
from backend.risk_ai.models.vendor_risk import score_vendors

_DEMO = os.path.join(os.path.dirname(__file__), "..", "backend", "ingestion", "dataset", "demo_scenarios")


def _demo_vendors():
    batch = IngestService(os.path.abspath(_DEMO)).process()
    assert batch["batch_metadata"]["rejected_total"] == 0
    graph = build_from_batch(batch)
    return {v.gstin: v for v in score_vendors(graph, reconcile(graph))}


def test_demo_scenarios_produce_controlled_outcomes():
    vendors = _demo_vendors()
    assert len(vendors) == 7

    normal = vendors["29AAAAA0001A1Z5"]
    assert (normal.score, normal.band, normal.evidence) == (0.0, "LOW", [])

    mismatch = vendors["29AAAAA0002B1Z5"]
    assert mismatch.score == 35.0 and mismatch.band == "MEDIUM"
    assert [e.finding for e in mismatch.evidence] == ["MISMATCH"]

    shortfall = vendors["29AAAAA0003C1Z5"]
    assert shortfall.score == 20.83 and shortfall.band == "LOW"
    assert any(e.finding == "TAX_SHORTFALL" for e in shortfall.evidence)

    for gstin in ("29AAAAA0005E1Z5", "29AAAAA0006F1Z5", "29AAAAA0008H1Z5"):
        v = vendors[gstin]
        assert v.score == 15.0
        assert any(e.finding == "CYCLE_MEMBERSHIP" for e in v.evidence)

    high = vendors["29AAAAA0007G1Z5"]
    assert high.score == 65.5 and high.band == "HIGH"
    assert {e.finding for e in high.evidence} == {"MISMATCH", "TAX_SHORTFALL", "CYCLE_MEMBERSHIP"}
