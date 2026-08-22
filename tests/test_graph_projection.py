"""Graph projection tests — offline batch path (no live Neo4j required)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import networkx as nx

from backend.graph.builder.projection import build_from_batch
from tests.test_ingest_service import _batch


def _g():
    return build_from_batch(_batch())


def test_projection_shape():
    g = _g()
    assert isinstance(g, nx.DiGraph)
    counts = {"Taxpayer": 0, "Invoice": 0, "ReturnFiling": 0, "Payment": 0, "IRN": 0}
    for _, d in g.nodes(data=True):
        counts[d["label"]] += 1
    assert counts == {"Taxpayer": 20, "Invoice": 100, "ReturnFiling": 40, "Payment": 20, "IRN": 90}


def test_all_seven_edge_types_present():
    types = {d["type"] for _, _, d in _g().edges(data=True)}
    assert types == {"SUPPLIED", "RECEIVED", "REPORTED_IN", "CLAIMED_IN", "REGISTERED", "FILED", "PAID_VIA"}


def test_claimed_in_carries_itc_amount():
    g = _g()
    claims = [(u, v, d) for u, v, d in g.edges(data=True) if d["type"] == "CLAIMED_IN"]
    assert claims and all("itcClaimed" in d and d["itcClaimed"] > 0 for _, _, d in claims)


def test_payment_chain_traversable():
    """Supplier -> Invoice -> GSTR1 return -> Payment must be walkable."""
    g = _g()
    supplier = next(n for n, d in g.nodes(data=True) if d["label"] == "Taxpayer")
    found = False
    for invoice in g.successors(supplier):
        for ret in g.successors(invoice):
            if g.nodes[ret].get("returnType") == "GSTR1":
                payments = [p for p in g.successors(ret) if g.nodes[p]["label"] == "Payment"]
                if payments:
                    found = True
    assert found
