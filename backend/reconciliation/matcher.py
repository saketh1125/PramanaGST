"""
Reconciliation Matcher — orchestrates graph-traversal queries to classify
every B2B Invoice node into a match status.

Three-way match logic (§20):
  FULL_MATCH        ← present in GSTR1 + GSTR2B + PR, values within ₹1 tolerance
  PARTIAL_MATCH     ← all sources present but values differ (also use VALUE_MISMATCH / TAX_MISMATCH)
  MISSING_IN_GSTR1  ← absent from GSTR1 but found in PR
  MISSING_IN_GSTR2B ← in GSTR1 but not in GSTR2B
  MISSING_IN_PR     ← in GSTR1/GSTR2B but not in Purchase Register
  VALUE_MISMATCH    ← taxable_value delta > ₹1
  TAX_MISMATCH      ← tax delta > ₹1 on same taxable base
  DATE_MISMATCH     ← invoice dates differ across sources
  ONLY_IN_GSTR1     ← present only in GSTR-1
  ONLY_IN_PR        ← present only in Purchase Register
"""
import logging
from decimal import Decimal
from typing import Dict, Any, List, Tuple

from backend.graph.connection import db
from backend.reconciliation import queries
from backend.reconciliation.mismatch_classifier import (
    classify_field_mismatches,
    compute_confidence_score,
)
from backend.reconciliation.itc_validator import check_itc_eligibility
from backend.schemas.reconciliation import (
    ReconciliationResult,
    ReconciliationSummary,
    MismatchDetail,
)

logger = logging.getLogger(__name__)

TOLERANCE = Decimal("1.00")
EXPECTED_SOURCES_B2B = {"GSTR1", "GSTR2B", "PURCHASE_REGISTER"}


def _determine_match_status(
    sources_present: List[str],
    mismatches: List[MismatchDetail],
) -> str:
    """
    Classify the reconciliation status from:
      • the set of source systems present
      • any field-level mismatch objects
    """
    present = set(sources_present)
    missing = EXPECTED_SOURCES_B2B - present

    # Presence-based classification (highest priority)
    if "GSTR1" not in present and "GSTR2B" not in present and "PURCHASE_REGISTER" in present:
        return "ONLY_IN_PR"
    if "GSTR1" in present and "GSTR2B" not in present and "PURCHASE_REGISTER" not in present:
        return "ONLY_IN_GSTR1"
    if "GSTR1" not in present:
        return "MISSING_IN_GSTR1"
    if "GSTR2B" not in present:
        return "MISSING_IN_GSTR2B"
    if "PURCHASE_REGISTER" not in present:
        return "MISSING_IN_PR"

    # All three sources found — check value consistency
    if not mismatches:
        return "FULL_MATCH"

    mismatch_fields = {m.field for m in mismatches}
    if "taxable_value" in mismatch_fields and "total_tax_amount" not in mismatch_fields:
        return "VALUE_MISMATCH"
    if "total_tax_amount" in mismatch_fields or "total_tax_amount (same_taxable_base)" in mismatch_fields:
        return "TAX_MISMATCH"

    return "PARTIAL_MATCH"


def _build_value_maps(observations: List[Dict[str, Any]]) -> Tuple[dict, dict]:
    """
    Produce per-source lookup dicts:
      taxable_value_by_source  →  { "GSTR1": 100000.0, ... }
      tax_amount_by_source     →  { "GSTR1": 18000.0, ... }
    """
    taxable_map: dict = {}
    tax_map: dict = {}
    for obs in observations:
        src = obs.get("source") or obs.get("source_system")
        if src:
            taxable_map[src] = float(obs.get("taxable") or 0)
            tax_map[src] = float(obs.get("tax") or 0)
    return taxable_map, tax_map


def reconcile_all() -> Tuple[ReconciliationSummary, List[ReconciliationResult]]:
    """
    Main entry point: runs Q4 against the graph, classifies every B2B invoice,
    runs ITC checks, and produces the result list + summary.
    """
    results: List[ReconciliationResult] = []
    circular_gstins = _get_circular_trading_gstins()

    with db.get_session() as session:
        raw = list(session.run(queries.Q4_FULL_RECONCILIATION))

    logger.info(f"Processing {len(raw)} B2B invoices for reconciliation.")

    for row in raw:
        entity_ref_id = row["entity_ref_id"]
        observations = list(row["observations"])       # list of dicts from collect()
        sources_present = [obs["source"] for obs in observations if obs.get("source")]
        sources_missing = list(EXPECTED_SOURCES_B2B - set(sources_present))

        # Field-level mismatch objects
        mismatches = classify_field_mismatches(observations)

        # Match status
        match_status = _determine_match_status(sources_present, mismatches)

        # Value maps
        taxable_by_src, tax_by_src = _build_value_maps(observations)

        # ITC eligibility
        itc_eligible, itc_reasons = check_itc_eligibility(entity_ref_id)

        # Confidence score
        score = compute_confidence_score(sources_present, mismatches)

        results.append(ReconciliationResult(
            entity_ref_id=entity_ref_id,
            invoice_number=row.get("invoice_number", ""),
            supplier_gstin=row.get("supplier_gstin", ""),
            recipient_gstin=row.get("recipient_gstin"),
            invoice_date=str(row.get("invoice_date", "")),
            financial_year=row.get("financial_year", ""),
            match_status=match_status,
            sources_present=sources_present,
            sources_missing=sources_missing,
            mismatches=mismatches,
            taxable_value_by_source=taxable_by_src,
            tax_amount_by_source=tax_by_src,
            itc_eligible=itc_eligible,
            itc_ineligibility_reasons=itc_reasons,
            confidence_score=score,
        ))

    summary = _build_summary(results)
    return summary, results


def _get_circular_trading_gstins() -> set:
    """
    Run Q6 to detect circular trading cycles; return set of involved GSTINs.
    """
    circular_gstins = set()
    try:
        with db.get_session() as session:
            rows = list(session.run(queries.Q6_CIRCULAR_TRADING))
        for row in rows:
            circular_gstins.update([row["gstin_a"], row["gstin_b"], row["gstin_c"]])
        if circular_gstins:
            logger.warning(f"Circular trading detected among: {circular_gstins}")
    except Exception as e:
        logger.error(f"Q6 circular trading query failed: {e}")
    return circular_gstins


def _build_summary(results: List[ReconciliationResult]) -> ReconciliationSummary:
    total = len(results)
    counters = {
        "full_match": 0, "partial_match": 0, "missing_in_gstr1": 0,
        "missing_in_gstr2b": 0, "missing_in_pr": 0, "value_mismatch": 0,
    }
    total_taxable = 0.0
    total_tax_at_risk = 0.0

    status_map = {
        "FULL_MATCH": "full_match",
        "PARTIAL_MATCH": "partial_match",
        "VALUE_MISMATCH": "value_mismatch",
        "TAX_MISMATCH": "value_mismatch",   # grouped under value_mismatch for summary
        "MISSING_IN_GSTR1": "missing_in_gstr1",
        "MISSING_IN_GSTR2B": "missing_in_gstr2b",
        "MISSING_IN_PR": "missing_in_pr",
        "ONLY_IN_GSTR1": "missing_in_gstr2b",
        "ONLY_IN_PR": "missing_in_gstr1",
    }

    for r in results:
        key = status_map.get(r.match_status)
        if key:
            counters[key] += 1
        taxable = sum(r.taxable_value_by_source.values()) / max(len(r.taxable_value_by_source), 1)
        total_taxable += taxable
        if r.match_status != "FULL_MATCH":
            tax = sum(r.tax_amount_by_source.values()) / max(len(r.tax_amount_by_source), 1)
            total_tax_at_risk += tax

    match_rate = round((counters["full_match"] / total) * 100, 2) if total else 0.0

    return ReconciliationSummary(
        total_invoices=total,
        full_match=counters["full_match"],
        partial_match=counters["partial_match"],
        missing_in_gstr1=counters["missing_in_gstr1"],
        missing_in_gstr2b=counters["missing_in_gstr2b"],
        missing_in_pr=counters["missing_in_pr"],
        value_mismatch=counters["value_mismatch"],
        total_taxable_value=total_taxable,
        total_tax_at_risk=total_tax_at_risk,
        match_rate_percent=match_rate,
    )


def get_circular_trading_report() -> List[Dict[str, Any]]:
    """
    Directly execute Q6 and return raw circular trading cycle data for the API.
    """
    try:
        with db.get_session() as session:
            rows = list(session.run(queries.Q6_CIRCULAR_TRADING))
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Circular trading query failed: {e}")
        return []
