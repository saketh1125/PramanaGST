"""
Mismatch Classifier — compares SourceObservation values across sources
and produces a list of MismatchDetail objects describing field-level deltas.
"""
from decimal import Decimal
from typing import List, Dict, Any

from backend.schemas.reconciliation import MismatchDetail

TOLERANCE = Decimal("1.00")           # ₹1.00 monetary tolerance
DATE_SENSITIVE_SOURCES = {"GSTR1", "GSTR2B", "PURCHASE_REGISTER"}


def _to_decimal(val) -> Decimal:
    if val is None:
        return Decimal("0.0")
    return Decimal(str(val))


def classify_field_mismatches(
    observations: List[Dict[str, Any]]
) -> List[MismatchDetail]:
    """
    Given a list of observation dicts (one per source system), compare each
    pair of sources on taxable_value, total_tax_amount, and (if available)
    invoice_date. Return a list of MismatchDetail objects.
    """
    mismatches: List[MismatchDetail] = []
    obs_by_source: Dict[str, Dict[str, Any]] = {}

    for obs in observations:
        src = obs.get("source") or obs.get("source_system")
        if src:
            obs_by_source[src] = obs

    sources = list(obs_by_source.keys())

    for i in range(len(sources)):
        for j in range(i + 1, len(sources)):
            src_a, src_b = sources[i], sources[j]
            obs_a, obs_b = obs_by_source[src_a], obs_by_source[src_b]

            # ── taxable_value ────────────────────────────────────────────────
            taxable_a = _to_decimal(obs_a.get("taxable"))
            taxable_b = _to_decimal(obs_b.get("taxable"))
            diff = abs(taxable_a - taxable_b)
            if diff > TOLERANCE:
                mismatches.append(MismatchDetail(
                    field="taxable_value",
                    source_a=src_a,
                    value_a=str(taxable_a),
                    source_b=src_b,
                    value_b=str(taxable_b),
                    difference=f"₹{diff}",
                ))

            # ── total_tax_amount ─────────────────────────────────────────────
            tax_a = _to_decimal(obs_a.get("tax"))
            tax_b = _to_decimal(obs_b.get("tax"))
            diff_tax = abs(tax_a - tax_b)
            if diff_tax > TOLERANCE:
                mismatches.append(MismatchDetail(
                    field="total_tax_amount",
                    source_a=src_a,
                    value_a=str(tax_a),
                    source_b=src_b,
                    value_b=str(tax_b),
                    difference=f"₹{diff_tax}",
                ))

            # ── IGST amount (inter-state invoices) ───────────────────────────
            igst_a = _to_decimal(obs_a.get("igst"))
            igst_b = _to_decimal(obs_b.get("igst"))
            diff_igst = abs(igst_a - igst_b)
            if diff_igst > TOLERANCE:
                mismatches.append(MismatchDetail(
                    field="igst_amount",
                    source_a=src_a,
                    value_a=str(igst_a),
                    source_b=src_b,
                    value_b=str(igst_b),
                    difference=f"₹{diff_igst}",
                ))

    return mismatches


def classify_tax_mismatches(
    observations: List[Dict[str, Any]]
) -> List[MismatchDetail]:
    """
    Focused comparison: taxable values match but tax computation differs.
    Useful for detecting wrong-rate application on the same base amount.
    """
    mismatches: List[MismatchDetail] = []
    obs_by_source: Dict[str, Dict[str, Any]] = {}
    for obs in observations:
        src = obs.get("source") or obs.get("source_system")
        if src:
            obs_by_source[src] = obs

    sources = list(obs_by_source.keys())
    for i in range(len(sources)):
        for j in range(i + 1, len(sources)):
            src_a, src_b = sources[i], sources[j]
            obs_a, obs_b = obs_by_source[src_a], obs_by_source[src_b]

            taxable_a = _to_decimal(obs_a.get("taxable"))
            taxable_b = _to_decimal(obs_b.get("taxable"))
            # If taxable values agree but taxes differ
            if abs(taxable_a - taxable_b) <= TOLERANCE:
                tax_a = _to_decimal(obs_a.get("tax"))
                tax_b = _to_decimal(obs_b.get("tax"))
                diff = abs(tax_a - tax_b)
                if diff > TOLERANCE:
                    mismatches.append(MismatchDetail(
                        field="total_tax_amount (same_taxable_base)",
                        source_a=src_a,
                        value_a=str(tax_a),
                        source_b=src_b,
                        value_b=str(tax_b),
                        difference=f"₹{diff}",
                    ))
    return mismatches


def compute_confidence_score(
    sources_present: List[str],
    mismatches: List[MismatchDetail]
) -> float:
    """
    Simple heuristic: 
      0.0 — no sources, 1.0 — all 3 sources present with zero mismatches.
    Deductions: -0.2 per missing expected source, -0.1 per mismatch.
    """
    expected = {"GSTR1", "GSTR2B", "PURCHASE_REGISTER"}
    present_set = set(sources_present)
    missing = expected - present_set

    score = 1.0 - (len(missing) * 0.2) - (len(mismatches) * 0.1)
    return max(0.0, round(score, 2))
