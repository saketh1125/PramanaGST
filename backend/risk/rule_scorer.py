from typing import Tuple, List, Dict, Any

def compute_rule_score(features: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    Executes the 11 deterministic Risk Scoring rules (RS-01 to RS-11).
    Returns a bounded score (0-100) and a list of human-readable triggered reasons.
    """
    total_score = 0.0
    triggered_rules = []

    # RS-01: Cancelled Registration
    if features.get("has_cancelled_registration"):
        total_score += 100 * 0.20
        triggered_rules.append("GST registration is CANCELLED")

    # RS-02 & RS-03: Mismatch Rates
    mismatch_rate = features.get("mismatch_rate", 0)
    if mismatch_rate > 0.3:
        total_score += 80 * 0.15
        triggered_rules.append(f"Mismatch rate is high ({mismatch_rate:.1%})")
    elif mismatch_rate > 0.1:
        total_score += 40 * 0.15
        triggered_rules.append(f"Mismatch rate is elevated ({mismatch_rate:.1%})")

    # RS-04: Missing in 2B Rate
    missing_2b = features.get("missing_in_2b_rate", 0)
    if missing_2b > 0.2:
        total_score += 70 * 0.10
        triggered_rules.append(f"High rate of invoices missing in GSTR-2B ({missing_2b:.1%})")

    # RS-05 & RS-06: Filing Regularity
    filing_reg = features.get("filing_regularity", 1.0)
    if filing_reg < 0.5:
        total_score += 90 * 0.15
        triggered_rules.append("Poor return filing regularity (filed < 50% of periods)")
    elif filing_reg < 0.8:
        total_score += 40 * 0.10
        triggered_rules.append("Irregular return filing behavior")

    # RS-07 & RS-08: Payment Coverage
    payment_cov = features.get("payment_coverage", 1.0)
    if payment_cov < 0.5:
        total_score += 80 * 0.10
        triggered_rules.append(f"Severe tax underpayment (Coverage: {payment_cov:.1%})")
    elif payment_cov < 0.8:
        total_score += 30 * 0.05
        triggered_rules.append(f"Partial tax payment detected (Coverage: {payment_cov:.1%})")

    # RS-09: Circular Trading
    if features.get("circular_trade_involved"):
        total_score += 100 * 0.10
        triggered_rules.append("Involved in detected circular trading pattern")

    # RS-10: Late Filings
    if features.get("late_filing_count", 0) > 2:
        total_score += 50 * 0.05
        triggered_rules.append("Persistent late filing of GST returns")

    # RS-11: Cancelled IRN
    if features.get("has_cancelled_irn"):
        total_score += 60 * 0.05
        triggered_rules.append("History of E-Invoice (IRN) cancellations post-issuance")

    # Bound to 0-100 scale because weights can exceed 100 in pathological scenarios
    # (Though weights sum to 1.10 here, making the absolute max ~110 without a cap)
    return min(total_score, 100.0), triggered_rules
