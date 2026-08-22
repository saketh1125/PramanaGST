"""
Reconciliation matcher — validates ITC claims by traversing the knowledge graph.

For every CLAIMED_IN edge (Invoice -> GSTR2B return) the engine walks:
    supplier Taxpayer <-SUPPLIED- Invoice -CLAIMED_IN-> GSTR2B Return
and compares claimed ITC against the invoice's reported tax components.

Outcomes:
  UNREPORTED  — claim exists but no REPORTED_IN edge to a GSTR-1 return (ghost billing)
  MATCHED     — |claimed - invoice tax| within tolerance
  MISMATCHED  — amounts diverge beyond tolerance
"""

from decimal import Decimal

TOLERANCE = Decimal("0.50")  # rupees; absorbs float/rounding noise


def _d(v) -> Decimal:
    return Decimal(str(v))


def _tax_total(invoice: dict) -> Decimal:
    return _d(invoice.get("igstAmount", 0)) + _d(invoice.get("cgstAmount", 0)) + _d(invoice.get("sgstAmount", 0))


def reconcile(graph, gstin: str | None = None) -> dict:
    """Reconcile all claims in *graph*, optionally scoped to one recipient GSTIN.

    Returns {"summary": {...}, "items": [...]} ready for ReconReport validation.
    """
    items = []
    g = graph

    for u, v, edge in list(g.edges(data=True)):
        if edge.get("type") != "CLAIMED_IN":
            continue
        invoice = g.nodes[u]
        claim_return = g.nodes[v]

        recipient = invoice.get("recipientGstin")
        if gstin and recipient != gstin:
            continue

        supplier = invoice["supplierGstin"]
        period = edge.get("claimPeriod", invoice.get("filingPeriod", ""))
        claimed = _d(edge.get("itcClaimed", 0))
        tax_total = _tax_total(invoice)

        # Ghost check: did the supplier actually report this invoice in GSTR-1?
        g1_returns = [
            w for w in g.successors(u)
            if g.edges[u, w].get("type") == "REPORTED_IN"
            and g.nodes[w].get("returnType") == "GSTR1"
        ]

        evidence = [
            f"Taxpayer:{supplier}",
            u,
            f"ReturnFiling:GSTR1-{supplier}-{invoice.get('filingPeriod')}",
            v,
        ]

        if not g1_returns:
            status, variance = "UNREPORTED", tax_total
        else:
            variance = tax_total - claimed
            if abs(variance) <= TOLERANCE:
                status, variance = "MATCHED", Decimal("0")
            else:
                status = "MISMATCHED"

        items.append({
            "claimRef": f"OBS-{recipient}|{invoice['invoiceNumber']}",
            "status": status,
            "invoiceNumber": invoice["invoiceNumber"],
            "supplierGstin": supplier,
            "recipientGstin": recipient,
            "period": period,
            "itcClaimed": str(claimed),
            "invoiceTaxTotal": str(tax_total),
            "variance": str(variance),
            "evidencePath": evidence,
        })

    matched = sum(1 for i in items if i["status"] == "MATCHED")
    mismatched = sum(1 for i in items if i["status"] == "MISMATCHED")
    unreported = sum(1 for i in items if i["status"] == "UNREPORTED")
    total = len(items)

    summary = {
        "totalClaims": total,
        "matched": matched,
        "mismatched": mismatched,
        "unreported": unreported,
        "claimedTotal": str(sum((_d(i["itcClaimed"]) for i in items), Decimal("0"))),
        "varianceTotal": str(sum((_d(i["variance"]) for i in items), Decimal("0"))),
        "matchRate": round(matched / total * 100, 2) if total else 0.0,
    }
    return {"summary": summary, "items": sorted(items, key=lambda x: x["claimRef"])}
