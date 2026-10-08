"""Milestone A — deterministic risk engine hardening.

Builds small synthetic NetworkX graphs (same node/edge conventions as
backend/graph/builder/projection.py) and pins scoring behavior:
zero-data vendors, boundary scores, monotonicity, tie-breaks,
determinism, division-by-zero guards, and known-limitation locks.
"""

import networkx as nx
import pytest

from backend.risk_ai.models.vendor_risk import BANDS, WEIGHTS, score_vendors


def _build(nodes, edges):
    g = nx.DiGraph()
    for nid, attrs in nodes:
        g.add_node(nid, **attrs)
    for u, v, t in edges:
        g.add_edge(u, v, type=t)
    return g


def _taxpayer(gstin, name=None):
    return (f"Taxpayer:{gstin}", {"label": "Taxpayer", "gstin": gstin, "legalName": name or gstin})


def _invoice(num, supplier, recipient):
    return (f"Invoice:{num}", {"label": "Invoice", "invoiceNumber": num,
                               "supplierGstin": supplier, "recipientGstin": recipient})


def _return(rid, rtype="GSTR1", liability="0.00"):
    return (f"ReturnFiling:{rid}", {"label": "ReturnFiling", "returnType": rtype,
                                   "totalTaxLiability": liability})


def _payment(pid, paid="0.00"):
    return (f"Payment:{pid}", {"label": "Payment", "totalPaid": paid})


def _items(specs):
    """specs: list of (supplier_gstin, status)."""
    return [{"supplierGstin": s, "status": st, "claimRef": f"OBS-{s}|INV{i:03d}",
             "evidencePath": [f"Taxpayer:{s}", f"Invoice:INV{i:03d}"]}
            for i, (s, st) in enumerate(specs)]


def _score(g, items):
    return score_vendors(g, {"items": items})


def _reported(gstin, inv, rid="R1"):
    return ([_return(f"{rid}-{gstin}"), ],
            [(f"Invoice:{inv}", f"ReturnFiling:{rid}-{gstin}", "REPORTED_IN")])


# ---------------------------------------------------------------- weights/bands

def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-12
    assert set(WEIGHTS) == {"mismatch", "ghost", "shortfall", "cycle"}


def test_band_threshold_semantics():
    at = lambda score: next(b for t, b in BANDS if score >= t)
    assert at(100.0) == "HIGH"
    assert at(60.0) == "HIGH"
    assert at(59.99) == "MEDIUM"
    assert at(30.0) == "MEDIUM"
    assert at(29.99) == "LOW"
    assert at(0.0) == "LOW"


# ------------------------------------------------------------------ zero data

def test_zero_invoice_vendor_scores_zero_low():
    g = _build([_taxpayer("29AAAAA0000A1Z5")], [])
    (v,) = _score(g, [])
    assert v.score == 0.0
    assert v.band == "LOW"
    assert v.reasons == []
    assert v.evidence == []
    s = v.signals
    assert (s.invoices_issued, s.mismatched_claims, s.unreported_invoices) == (0, 0, 0)


def test_empty_graph_returns_no_vendors():
    assert score_vendors(nx.DiGraph(), {"items": []}) == []


def test_ghost_only_scores_25_low():
    g = _build([_taxpayer("29AAAAA0000A1Z5"), _invoice("I1", "29AAAAA0000A1Z5", "29BBBBB0000B1Z5")],
               [("Taxpayer:29AAAAA0000A1Z5", "Invoice:I1", "SUPPLIED")])
    (v,) = _score(g, [])
    assert v.score == 25.0
    assert v.band == "LOW"
    assert v.signals.unreported_invoices == 1


# ------------------------------------------------------------- liability/paid

def test_zero_liability_zero_paid_no_shortfall():
    nodes = [_taxpayer("29AAAAA0000A1Z5"), _invoice("I1", "29AAAAA0000A1Z5", "29BBBBB0000B1Z5"),
             _return("R1-29AAAAA0000A1Z5")]
    edges = [("Taxpayer:29AAAAA0000A1Z5", "Invoice:I1", "SUPPLIED"),
             ("Invoice:I1", "ReturnFiling:R1-29AAAAA0000A1Z5", "REPORTED_IN"),
             ("Taxpayer:29AAAAA0000A1Z5", "ReturnFiling:R1-29AAAAA0000A1Z5", "FILED")]
    (v,) = _score(_build(nodes, edges), [])
    assert v.score == 0.0
    assert v.band == "LOW"
    assert v.signals.shortfall == "0.00"
    assert not any(e.finding == "TAX_SHORTFALL" for e in v.evidence)


def test_overpayment_ignored():
    nodes = [_taxpayer("29AAAAA0000A1Z5"), _invoice("I1", "29AAAAA0000A1Z5", "29BBBBB0000B1Z5"),
             _return("R1-29AAAAA0000A1Z5", liability="100.00"), _payment("P1", paid="150.00")]
    edges = [("Taxpayer:29AAAAA0000A1Z5", "Invoice:I1", "SUPPLIED"),
             ("Invoice:I1", "ReturnFiling:R1-29AAAAA0000A1Z5", "REPORTED_IN"),
             ("Taxpayer:29AAAAA0000A1Z5", "ReturnFiling:R1-29AAAAA0000A1Z5", "FILED"),
             ("ReturnFiling:R1-29AAAAA0000A1Z5", "Payment:P1", "PAID_VIA")]
    (v,) = _score(_build(nodes, edges), [])
    assert v.score == 0.0
    assert v.signals.shortfall == "0.00"
    assert not any("shortfall" in r for r in v.reasons)


def test_full_shortfall_ratio_one():
    nodes = [_taxpayer("29AAAAA0000A1Z5"), _invoice("I1", "29AAAAA0000A1Z5", "29BBBBB0000B1Z5"),
             _return("R1-29AAAAA0000A1Z5", liability="100.00")]
    edges = [("Taxpayer:29AAAAA0000A1Z5", "Invoice:I1", "SUPPLIED"),
             ("Invoice:I1", "ReturnFiling:R1-29AAAAA0000A1Z5", "REPORTED_IN"),
             ("Taxpayer:29AAAAA0000A1Z5", "ReturnFiling:R1-29AAAAA0000A1Z5", "FILED")]
    (v,) = _score(_build(nodes, edges), [])
    assert v.score == 25.0
    assert any(e.finding == "TAX_SHORTFALL" for e in v.evidence)


# ----------------------------------------------------------------- mismatches

def test_all_mismatched_scores_35_medium():
    g = _build(
        [_taxpayer("29AAAAA0000A1Z5"),
         _invoice("I1", "29AAAAA0000A1Z5", "29BBBBB0000B1Z5"),
         _invoice("I2", "29AAAAA0000A1Z5", "29BBBBB0000B1Z5"),
         _invoice("I3", "29AAAAA0000A1Z5", "29BBBBB0000B1Z5"),
         _return("R-A")] ,
        [("Taxpayer:29AAAAA0000A1Z5", "Invoice:I1", "SUPPLIED"),
         ("Taxpayer:29AAAAA0000A1Z5", "Invoice:I2", "SUPPLIED"),
         ("Taxpayer:29AAAAA0000A1Z5", "Invoice:I3", "SUPPLIED"),
         ("Invoice:I1", "ReturnFiling:R-A", "REPORTED_IN"),
         ("Invoice:I2", "ReturnFiling:R-A", "REPORTED_IN"),
         ("Invoice:I3", "ReturnFiling:R-A", "REPORTED_IN")])
    items = _items([("29AAAAA0000A1Z5", "MISMATCHED")] * 3)
    (v,) = _score(g, items)
    assert v.score == 35.0
    assert v.band == "MEDIUM"
    ev = next(e for e in v.evidence if e.finding == "MISMATCH")
    assert ev.observed == "3/3" and ev.ratio == 1.0


def test_exactly_sixty_is_high():
    g = _build(
        [_taxpayer("29AAAAA0000A1Z5"), _invoice("I1", "29AAAAA0000A1Z5", "29BBBBB0000B1Z5"),
         _return("R1-29AAAAA0000A1Z5", liability="100.00")],
        [("Taxpayer:29AAAAA0000A1Z5", "Invoice:I1", "SUPPLIED"),
         ("Invoice:I1", "ReturnFiling:R1-29AAAAA0000A1Z5", "REPORTED_IN"),
         ("Taxpayer:29AAAAA0000A1Z5", "ReturnFiling:R1-29AAAAA0000A1Z5", "FILED")])
    (v,) = _score(g, _items([("29AAAAA0000A1Z5", "MISMATCHED")]))
    assert v.score == 60.0
    assert v.band == "HIGH"


# --------------------------------------------------------------------- cycles

def test_two_vendor_cycle_flags_both():
    a, b = "29AAAAA0000A1Z5", "29BBBBB0000B1Z5"
    g = _build(
        [_taxpayer(a), _taxpayer(b),
         _invoice("I1", a, b), _invoice("I2", b, a), _return("R-A")],
        [(f"Taxpayer:{a}", "Invoice:I1", "SUPPLIED"),
         (f"Taxpayer:{b}", "Invoice:I2", "SUPPLIED"),
         ("Invoice:I1", "ReturnFiling:R-A", "REPORTED_IN"),
         ("Invoice:I2", "ReturnFiling:R-A", "REPORTED_IN")])
    vendors = {v.gstin: v for v in _score(g, [])}
    for gstin in (a, b):
        v = vendors[gstin]
        assert v.signals.in_cycle is True
        assert v.score == 15.0
        ev = next(e for e in v.evidence if e.finding == "CYCLE_MEMBERSHIP")
        assert ev.cycle_size == 2 and ev.member_gstins == sorted([a, b])


def test_self_loop_not_flagged_as_cycle():
    # Known limitation: flow projection drops s == r edges, so the
    # single-node self-edge branch in _cycle_components is unreachable.
    x = "29AAAAA0000A1Z5"
    g = _build([_taxpayer(x), _invoice("I1", x, x), _return("R-A")],
               [(f"Taxpayer:{x}", "Invoice:I1", "SUPPLIED"),
                ("Invoice:I1", "ReturnFiling:R-A", "REPORTED_IN")])
    (v,) = _score(g, [])
    assert v.signals.in_cycle is False
    assert v.score == 0.0


def test_cycle_term_adds_exactly_fifteen():
    a, b = "29AAAAA0000A1Z5", "29BBBBB0000B1Z5"
    base_nodes = [_taxpayer(a), _taxpayer(b), _return("R-A")]
    base_edges = [("Invoice:I1", "ReturnFiling:R-A", "REPORTED_IN")]
    plain = _build(base_nodes + [_invoice("I1", a, "29CCCCC0000C1Z5")],
                   base_edges + [(f"Taxpayer:{a}", "Invoice:I1", "SUPPLIED")])
    looped = _build(base_nodes + [_invoice("I1", a, b), _invoice("I2", b, a)],
                    base_edges + [(f"Taxpayer:{a}", "Invoice:I1", "SUPPLIED"),
                                  (f"Taxpayer:{b}", "Invoice:I2", "SUPPLIED"),
                                  ("Invoice:I2", "ReturnFiling:R-A", "REPORTED_IN")])
    (v_plain,) = [v for v in _score(plain, []) if v.gstin == a]
    v_looped = next(v for v in _score(looped, []) if v.gstin == a)
    assert v_looped.score - v_plain.score == 15.0


# --------------------------------------------------------------- monotonicity

def _mismatch_graph(gstin, n_issued, n_mismatched):
    nodes = [_taxpayer(gstin), _return("R-A")]
    edges = []
    for i in range(n_issued):
        inv = f"I{i}"
        nodes.append(_invoice(inv, gstin, "29ZZZZZ0000Z1Z5"))
        edges.append((f"Taxpayer:{gstin}", f"Invoice:{inv}", "SUPPLIED"))
        edges.append((f"Invoice:{inv}", "ReturnFiling:R-A", "REPORTED_IN"))
    items = _items([(gstin, "MISMATCHED")] * n_mismatched + [(gstin, "MATCHED")] * (n_issued - n_mismatched))
    return _build(nodes, edges), items


def test_increasing_mismatch_never_reduces_score():
    scores = []
    for k in (0, 1, 3, 4):
        g, items = _mismatch_graph("29AAAAA0000A1Z5", 4, k)
        (v,) = _score(g, items)
        scores.append(v.score)
    assert scores == sorted(scores)
    assert scores[0] < scores[-1]


def test_increasing_shortfall_never_reduces_score():
    def run(paid):
        nodes = [_taxpayer("29AAAAA0000A1Z5"), _invoice("I1", "29AAAAA0000A1Z5", "29BBBBB0000B1Z5"),
                 _return("R1", liability="100.00"), _payment("P1", paid=paid)]
        edges = [("Taxpayer:29AAAAA0000A1Z5", "Invoice:I1", "SUPPLIED"),
                 ("Invoice:I1", "ReturnFiling:R1", "REPORTED_IN"),
                 ("Taxpayer:29AAAAA0000A1Z5", "ReturnFiling:R1", "FILED"),
                 ("ReturnFiling:R1", "Payment:P1", "PAID_VIA")]
        (v,) = _score(_build(nodes, edges), [])
        return v.score
    assert run("90.00") < run("50.00") < run("10.00") < run("0.00")


# ------------------------------------------------------- determinism/ordering

def test_repeated_execution_is_deterministic():
    g, items = _mismatch_graph("29AAAAA0000A1Z5", 4, 2)
    first = [v.model_dump(by_alias=True) for v in _score(g, items)]
    second = [v.model_dump(by_alias=True) for v in _score(g, items)]
    assert first == second


def test_ties_break_by_gstin_not_insertion_order():
    # Insert B first; output must still be gstin-sorted on ties.
    g = _build([_taxpayer("29BBBBB0000B1Z5"), _taxpayer("29AAAAA0000A1Z5")], [])
    assert [v.gstin for v in _score(g, [])] == ["29AAAAA0000A1Z5", "29BBBBB0000B1Z5"]


# ------------------------------------------------------------- missing data

def test_orphan_recon_supplier_ignored():
    g = _build([_taxpayer("29AAAAA0000A1Z5")], [])
    assert [v.gstin for v in _score(g, _items([("29ZZZZZ0000Z1Z5", "MISMATCHED")]))] == ["29AAAAA0000A1Z5"]


def test_taxpayer_absent_from_recon_uses_invoice_fallback():
    g = _build([_taxpayer("29AAAAA0000A1Z5"), _invoice("I1", "29AAAAA0000A1Z5", "29BBBBB0000B1Z5"),
                _return("R-A")],
               [("Taxpayer:29AAAAA0000A1Z5", "Invoice:I1", "SUPPLIED"),
                ("Invoice:I1", "ReturnFiling:R-A", "REPORTED_IN")])
    (v,) = _score(g, [])
    assert v.signals.mismatched_claims == 0
    assert v.signals.invoices_issued == 1
    assert not any(e.finding == "MISMATCH" for e in v.evidence)


def test_missing_items_key_raises_keyerror():
    # Known strictness: recon_report must carry "items"; documents the
    # current behavior rather than silently scoring empty input.
    g = _build([_taxpayer("29AAAAA0000A1Z5")], [])
    with pytest.raises(KeyError):
        score_vendors(g, {})


def test_high_band_always_has_reasons():
    g, items = _mismatch_graph("29AAAAA0000A1Z5", 2, 2)
    nodes_extra = [_return("R1", liability="50.00")]
    g.add_node("ReturnFiling:R1", **dict(nodes_extra[0][1]))
    g.add_edge("Taxpayer:29AAAAA0000A1Z5", "ReturnFiling:R1", type="FILED")
    (v,) = _score(g, items)
    assert v.band == "HIGH"
    assert len(v.reasons) >= 1
    assert len(v.evidence) >= 1
