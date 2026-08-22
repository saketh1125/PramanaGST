"""
Vendor risk scoring — deterministic rule engine over the knowledge graph.

Signals per supplier:
  mismatch_rate     share of their invoices whose ITC claims diverge
  ghost_rate        share of supplied invoices never reported in a GSTR-1 return
  shortfall_ratio   unpaid tax vs filed liability (PAID_VIA chain)
  cycle_member      participates in a directed trading loop (circular trading)

Score = 100 * Σ(weight × signal). Deterministic, explainable, no ML theater
on synthetic data — swap in a trained model behind the same interface later.
"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

WEIGHTS = {"mismatch": 0.35, "ghost": 0.25, "shortfall": 0.25, "cycle": 0.15}
BANDS = [(60.0, "HIGH"), (30.0, "MEDIUM"), (0.0, "LOW")]


class RiskSignal(BaseModel):
    model_config = ConfigDict(json_schema_extra={"entity": "RISK_SIGNAL", "contract_version": "1.0.0"})

    invoices_issued: int = Field(..., alias="invoicesIssued", ge=0)
    mismatched_claims: int = Field(..., alias="mismatchedClaims", ge=0)
    unreported_invoices: int = Field(..., alias="unreportedInvoices", ge=0)
    tax_liability: str = Field(..., alias="taxLiability")
    tax_paid: str = Field(..., alias="taxPaid")
    shortfall: str = Field(default="0.00", alias="shortfall")
    in_cycle: bool = Field(..., alias="inCycle")


class VendorRisk(BaseModel):
    model_config = ConfigDict(json_schema_extra={"entity": "VENDOR_RISK", "contract_version": "1.0.0"})

    gstin: str
    legal_name: str = Field(..., alias="legalName")
    score: float = Field(..., ge=0, le=100)
    band: str = Field(..., description="HIGH / MEDIUM / LOW")
    reasons: list[str] = Field(default_factory=list)
    signals: RiskSignal


def _d(v) -> Decimal:
    return Decimal(str(v))


def _taxpayer_flow_graph(graph):
    """Project Taxpayer->Taxpayer supply edges from Invoice nodes."""
    import networkx as nx

    flow = nx.DiGraph()
    for n, data in graph.nodes(data=True):
        if data.get("label") != "Invoice":
            continue
        s, r = data.get("supplierGstin"), data.get("recipientGstin")
        if s and r and s != r:
            flow.add_edge(s, r)
    return flow


# ponytail: nx.simple_cycles over full taxpayer flow — fine <=10k taxpayers;
# switch to strongly-connected-component pruning for production volumes
def _cycle_nodes(flow) -> set[str]:
    import networkx as nx

    members: set[str] = set()
    for comp in nx.strongly_connected_components(flow):
        if len(comp) > 1:
            members |= comp
        elif len(comp) == 1:
            node = next(iter(comp))
            if flow.has_edge(node, node):
                members.add(node)
    return members


def score_vendors(graph, recon_report: dict) -> list[VendorRisk]:
    """Score every taxpayer that issued at least one invoice."""
    g = graph
    recon_by_supplier: dict[str, dict] = {}
    for item in recon_report["items"]:
        recon_by_supplier.setdefault(item["supplierGstin"], {
            "issued": 0, "mismatched": 0,
        })
        entry = recon_by_supplier[item["supplierGstin"]]
        entry["issued"] += 1
        if item["status"] == "MISMATCHED":
            entry["mismatched"] += 1

    flow = _taxpayer_flow_graph(g)
    cyc = _cycle_nodes(flow)

    vendors: list[VendorRisk] = []
    for n, data in g.nodes(data=True):
        if data.get("label") != "Taxpayer":
            continue
        gstin = data["gstin"]

        issued_invoices = [
            inv for inv in g.nodes
            if g.nodes[inv].get("label") == "Invoice" and g.has_edge(n, inv)
            and g.edges[n, inv].get("type") == "SUPPLIED"
        ]

        unreported = sum(
            1 for inv in issued_invoices
            if not any(
                g.edges[inv, w].get("type") == "REPORTED_IN"
                for w in g.successors(inv)
                if w.startswith("ReturnFiling:")
            )
        )

        # Liability vs paid via GSTR-1 -> Payment chain
        liability = Decimal("0")
        paid = Decimal("0")
        for ret in g.successors(n):
            if g.edges[n, ret].get("type") != "FILED":
                continue
            ret_data = g.nodes[ret]
            if ret_data.get("returnType") != "GSTR1":
                continue
            liability += _d(ret_data.get("totalTaxLiability", 0))
            for pay in g.successors(ret):
                if g.edges[ret, pay].get("type") == "PAID_VIA":
                    paid += _d(g.nodes[pay].get("totalPaid", 0))

        shortfall = max(liability - paid, Decimal("0"))
        shortfall_ratio = float(shortfall / liability) if liability > 0 else 0.0

        stats = recon_by_supplier.get(gstin, {"issued": len(issued_invoices), "mismatched": 0})
        mismatch_rate = stats["mismatched"] / stats["issued"] if stats["issued"] else 0.0
        ghost_rate = unreported / len(issued_invoices) if issued_invoices else 0.0
        in_cycle = gstin in cyc

        raw = (
            WEIGHTS["mismatch"] * mismatch_rate
            + WEIGHTS["ghost"] * ghost_rate
            + WEIGHTS["shortfall"] * min(shortfall_ratio, 1.0)
            + WEIGHTS["cycle"] * (1.0 if in_cycle else 0.0)
        )
        score = round(raw * 100, 2)
        band = next(b for threshold, b in BANDS if score >= threshold)

        reasons = []
        if mismatch_rate > 0:
            reasons.append(f"{stats['mismatched']} of {stats['issued']} invoices have ITC claim mismatches")
        if unreported:
            reasons.append(f"{unreported} invoices never reported in any GSTR-1 return (ghost billing)")
        if shortfall > 0:
            reasons.append(f"tax shortfall of INR {shortfall} against filed liability")
        if in_cycle:
            reasons.append("participates in a circular trading loop")

        vendors.append(VendorRisk(
            gstin=gstin,
            legalName=data.get("legalName", gstin),
            score=score,
            band=band,
            reasons=reasons,
            signals=RiskSignal(
                invoicesIssued=len(issued_invoices),
                mismatchedClaims=stats["mismatched"],
                unreportedInvoices=unreported,
                taxLiability=str(liability),
                taxPaid=str(paid),
                shortfall=str(shortfall),
                inCycle=in_cycle,
            ),
        ))

    vendors.sort(key=lambda v: -v.score)
    return vendors
