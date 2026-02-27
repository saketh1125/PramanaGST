from typing import Dict, Any, List

def generate_explanation(
    legal_name: str,
    gstin: str,
    composite_score: float,
    risk_level: str,
    features: Dict[str, Any],
    triggered_rules: List[str]
) -> str:
    """
    Generates a natural language explanation for a vendor's risk score.
    Follows the template structure dictated in §28.
    """
    parts = []

    # Intro sentence
    parts.append(
        f"Vendor {legal_name} ({gstin}) has a {risk_level} risk score of "
        f"{composite_score:.1f}/100."
    )

    # 1. Registration Status Check
    if "has_cancelled_registration" in features and features["has_cancelled_registration"]:
        parts.append(
            "⚠️ This vendor's GST registration is CANCELLED, "
            "making all ITC claims against their invoices ineligible."
        )

    # 2. Mismatch Volume Check
    mismatch_rate = features.get("mismatch_rate", 0.0)
    mismatch_count = features.get("mismatch_count", 0)
    total_invoices = features.get("total_invoices_issued", 0)
    
    if mismatch_rate > 0:
        parts.append(
            f"📊 {mismatch_count} out of {total_invoices} invoices "
            f"({mismatch_rate:.0%}) show discrepancies across "
            "GSTR-1, GSTR-2B, and purchase records."
        )

    # 3. Missing in 2B Check
    missing_in_2b_rate = features.get("missing_in_2b_rate", 0.0)
    missing_in_2b_count = features.get("missing_in_2b_count", 0)
    
    if missing_in_2b_rate > 0:
        parts.append(
            f"🔍 {missing_in_2b_count} invoices issued by this vendor "
            "do not appear in buyers' GSTR-2B, suggesting "
            "potential non-filing or delayed reporting."
        )

    # 4. Payment Coverage Check
    payment_coverage = features.get("payment_coverage", 1.0)
    total_paid = features.get("total_paid", 0.0)
    total_taxable = features.get("total_taxable_value", 0.0)
    
    if payment_coverage < 1.0 and payment_coverage > 0: # Avoid noise on zero liability cases
        parts.append(
            f"💰 Tax payment coverage is {payment_coverage:.0%}. "
            f"The vendor has paid ₹{total_paid:,.2f} against "
            f"a liability of ₹{total_taxable:,.2f}."
        )
    elif payment_coverage == 0.0 and total_taxable > 0:
        parts.append(
             f"💰 Zero tax payment detected. The vendor has paid ₹{total_paid:,.2f} "
             f"against a liability of ₹{total_taxable:,.2f}."
        )

    # 5. Graph Anomaly: Circular Trade Check
    if features.get("circular_trade_involved"):
        parts.append(
            "🔄 This vendor is involved in a circular trading pattern, "
            "which is a known indicator of fraudulent ITC claims."
        )

    # 6. Filing Regularity Check
    filing_regularity = features.get("filing_regularity", 1.0)
    returns_filed = features.get("returns_filed", 0)
    expected_periods = 3 # Hardcoded to match feature_engineer abstraction
    
    if filing_regularity < 1.0:
        parts.append(
            f"📅 Filing regularity is {filing_regularity:.0%}. "
            f"Returns were filed for {returns_filed} out of "
            f"{expected_periods} expected periods."
        )

    # Combine parts cleanly
    return " ".join(parts)
