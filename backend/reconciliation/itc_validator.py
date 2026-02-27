"""
ITC Validator — multi-hop graph checks to determine Input Tax Credit eligibility.

Eligibility requires ALL of the following:
  1. Invoice is present in the buyer's GSTR-2B (auto-populated).
  2. Supplier's GST registration is ACTIVE.
  3. If an IRN exists, it must not be CANCELLED.
  4. Supplier has filed GSTR-1 for the relevant tax period.
"""
from typing import Dict, Any, Tuple, List

from backend.graph.connection import db
from backend.reconciliation.queries import Q5_ITC_ELIGIBILITY


def check_itc_eligibility(entity_ref_id: str) -> Tuple[bool, List[str]]:
    """
    Run the multi-hop Q5 query against Neo4j for a single invoice,
    then apply programmatic ITC rules on top.

    Returns:
        (is_eligible: bool, ineligibility_reasons: list[str])
    """
    reasons: List[str] = []
    is_eligible = True

    try:
        with db.get_session() as session:
            result = session.run(Q5_ITC_ELIGIBILITY, entity_ref_id=entity_ref_id)
            records = list(result)
    except Exception as e:
        return False, [f"Graph query failed: {e}"]

    if not records:
        return False, ["Invoice not found in graph or not B2B type"]

    # Evaluate the first (or most specific) record returned
    row = records[0]

    in_gstr2b: bool = row.get("in_gstr2b", False)
    supplier_status: str = row.get("supplier_status", "UNKNOWN")
    irn_status: str = row.get("irn_status")
    filing_status: str = row.get("supplier_filing_status")

    # Rule 1 — Invoice must appear in GSTR-2B
    if not in_gstr2b:
        reasons.append("Invoice not present in buyer's GSTR-2B")
        is_eligible = False

    # Rule 2 — Supplier registration must be ACTIVE
    if supplier_status in ("CANCELLED", "SUSPENDED"):
        reasons.append(
            f"Supplier GSTIN registration is {supplier_status}; ITC disallowed"
        )
        is_eligible = False

    # Rule 3 — IRN (if any) must not be CANCELLED
    if irn_status == "CANCELLED":
        reasons.append("E-Invoice IRN has been CANCELLED; ITC not claimable")
        is_eligible = False

    # Rule 4 — Supplier must have filed GSTR-1 for this period
    if filing_status in ("NOT_FILED", None):
        reasons.append(
            "Supplier has not filed GSTR-1 for the relevant period; ITC at risk"
        )
        is_eligible = False

    return is_eligible, reasons


def batch_check_itc(entity_ref_ids: List[str]) -> Dict[str, Tuple[bool, List[str]]]:
    """
    Run ITC eligibility checks for a batch of invoices.
    Returns a dict keyed by entity_ref_id.
    """
    return {eid: check_itc_eligibility(eid) for eid in entity_ref_ids}
