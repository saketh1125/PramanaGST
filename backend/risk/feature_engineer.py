"""
Feature Engineer — Extracts graph topological data and structural
mismatch records to compute the numerical feature vector per Vendor.
"""
import logging
from typing import Dict, Any, List

from backend.graph.connection import db

logger = logging.getLogger(__name__)

# Query defining the aggregation of per-vendor features directly from the Knowledge Graph
Q_VENDOR_FEATURES = """
MATCH (t:Taxpayer {gstin: $gstin})
OPTIONAL MATCH (t)<-[:ISSUED_BY]-(i:Invoice)
OPTIONAL MATCH (i)-[:HAS_OBSERVATION]->(o:SourceObservation)

WITH t, i, o
WITH t,
     count(DISTINCT i) AS total_invoices_issued,
     sum(CASE WHEN o.source_system = 'GSTR1' THEN o.taxable_value ELSE 0 END) AS total_taxable_value,
     max(CASE WHEN o.source_system = 'GSTR1' THEN o.taxable_value ELSE 0 END) AS max_invoice_value,
     count(DISTINCT i.recipient_gstin) AS unique_buyers

OPTIONAL MATCH (t)-[:FILED]->(r:Return)
WITH t, total_invoices_issued, total_taxable_value, max_invoice_value, unique_buyers,
     count(r) AS returns_filed,
     sum(CASE WHEN r.filing_status = 'LATE_FILED' THEN 1 ELSE 0 END) AS late_filings

OPTIONAL MATCH (t)-[:PAID_TAX_IN]->(p:Payment)
WITH t, total_invoices_issued, total_taxable_value, max_invoice_value, unique_buyers,
     returns_filed, late_filings,
     sum(p.total_paid) AS total_paid

RETURN t.gstin AS gstin,
       t.legal_name AS legal_name,
       t.status AS status,
       total_invoices_issued,
       total_taxable_value,
       max_invoice_value,
       unique_buyers,
       returns_filed,
       late_filings,
       total_paid,
       CASE WHEN total_taxable_value > 0 
            THEN total_paid / total_taxable_value 
            ELSE 1.0 END AS payment_coverage
"""


def compute_vendor_features(
    gstin: str, 
    reconciliation_results: List[Any], 
    circular_trade_gstins: set
) -> Dict[str, Any]:
    """
    Combines the Neo4j aggregation with the latest reconciliation results
    for a specific vendor to construct the full feature vector.
    """
    try:
        with db.get_session() as session:
            raw = list(session.run(Q_VENDOR_FEATURES, gstin=gstin))
    except Exception as e:
        logger.error(f"Error executing feature query for {gstin}: {e}")
        return _empty_features(gstin)

    if not raw:
        return _empty_features(gstin)
        
    row = raw[0]

    # Filter reconciliation results meant for this vendor
    vendor_recons = [r for r in reconciliation_results if getattr(r, "supplier_gstin", "") == gstin]
    
    total_invoices = row["total_invoices_issued"]
    mismatch_count = 0
    missing_in_2b_count = 0
    value_mismatch_total = 0.0
    has_cancelled_irn = False
    
    for r in vendor_recons:
        # Check mismatch rates
        if r.match_status != "FULL_MATCH":
            mismatch_count += 1
        
        # Check missing in 2B
        if r.match_status == "MISSING_IN_GSTR2B":
            missing_in_2b_count += 1
            
        # Accumulate risk value
        if r.match_status in ("VALUE_MISMATCH", "TAX_MISMATCH", "PARTIAL_MATCH"):
            # Use max taxable as proxy for at risk
            value_mismatch_total += max(r.taxable_value_by_source.values() or [0])
            
        # Check IRN cancellations
        # Note: In real setup, you might query graph again or rely on recon object if it tracks it.
        # Assuming r tracks itc_ineligibility_reasons mentioning "CANCELLED"
        if any("CANCELLED" in reason for reason in getattr(r, "itc_ineligibility_reasons", [])):
            has_cancelled_irn = True

    # Derived rates
    mismatch_rate = mismatch_count / total_invoices if total_invoices > 0 else 0.0
    missing_in_2b_rate = missing_in_2b_count / total_invoices if total_invoices > 0 else 0.0
    
    # Filing regularity (assume 3 expected periods for the MVP snapshot dataset)
    expected_periods = 3
    filing_regularity = row["returns_filed"] / expected_periods

    features = {
        "gstin": row["gstin"],
        "legal_name": row["legal_name"],
        "has_cancelled_registration": (row["status"] == "CANCELLED"),
        "total_invoices_issued": total_invoices,
        "total_taxable_value": row["total_taxable_value"],
        "max_invoice_value": row["max_invoice_value"],
        "avg_invoice_value": row["total_taxable_value"] / total_invoices if total_invoices > 0 else 0,
        "unique_buyers": row["unique_buyers"],
        "mismatch_count": mismatch_count,
        "mismatch_rate": mismatch_rate,
        "missing_in_2b_count": missing_in_2b_count,
        "missing_in_2b_rate": missing_in_2b_rate,
        "value_mismatch_total": value_mismatch_total,
        "payment_coverage": row["payment_coverage"],
        "returns_filed": row["returns_filed"],
        "late_filing_count": row["late_filings"],
        "filing_regularity": min(filing_regularity, 1.0), # cap at 1.0
        "has_cancelled_irn": has_cancelled_irn,
        "circular_trade_involved": gstin in circular_trade_gstins,
        "total_paid": row["total_paid"]
    }
    
    return features

def _empty_features(gstin: str) -> Dict[str, Any]:
    return {
        "gstin": gstin,
        "legal_name": "UNKNOWN",
        "has_cancelled_registration": False,
        "total_invoices_issued": 0,
        "total_taxable_value": 0.0,
        "max_invoice_value": 0.0,
        "avg_invoice_value": 0.0,
        "unique_buyers": 0,
        "mismatch_count": 0,
        "mismatch_rate": 0.0,
        "missing_in_2b_count": 0,
        "missing_in_2b_rate": 0.0,
        "value_mismatch_total": 0.0,
        "payment_coverage": 1.0,
        "returns_filed": 0,
        "late_filing_count": 0,
        "filing_regularity": 0.0,
        "has_cancelled_irn": False,
        "circular_trade_involved": False,
        "total_paid": 0.0
    }
