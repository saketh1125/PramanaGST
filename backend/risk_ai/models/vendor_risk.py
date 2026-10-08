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


class EvidenceItem(BaseModel):
    """Traceable source fact backing one deterministic risk finding."""

    model_config = ConfigDict(json_schema_extra={"entity": "RISK_EVIDENCE", "contract_version": "1.0.0"})

    finding: str                      # "MISMATCH" | "GHOST_UNREPORTED" | "TAX_SHORTFALL" | "CYCLE_MEMBERSHIP"
    source: str                       # "reconciliation" | "knowledge_graph"
    observed: str                     # "37/82" style summary of the measurement
    description: str = ""
    ratio: Optional[float] = None
    liability: Optional[str] = None
    paid: Optional[str] = None
    shortfall: Optional[str] = None
    cycle_size: Optional[int] = Field(default=None, alias="cycleSize")
    member_gstins: list[str] = Field(default_factory=list, alias="memberGstins")
    item_refs: list[str] = Field(default_factory=list, alias="itemRefs")
    node_ids: list[str] = Field(default_factory=list, alias="nodeIds")
    path: Optional[list[str]] = None


class VendorRisk(BaseModel):
    model_config = ConfigDict(json_schema_extra={"entity": "VENDOR_RISK", "contract_version": "1.0.0"})

    gstin: str
    legal_name: str = Field(..., alias="legalName")
    score: float = Field(..., ge=0, le=100)
    band: str = Field(..., description="HIGH / MEDIUM / LOW")
    reasons: list[str] = Field(default_factory=list)
    signals: RiskSignal
    evidence: list[EvidenceItem] = Field(default_factory=list)


def _d(v) -> Decimal:
    return Decimal(str(v))


def _money(d: Decimal) -> str:
    """Canonical 2dp money string (matches the "0.00" schema default)."""
    return str(d.quantize(Decimal("0.00")))


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
def _cycle_components(flow) -> list[set[str]]:
    import networkx as nx

    return [comp for comp in nx.strongly_connected_components(flow)
            if len(comp) > 1 or (len(comp) == 1 and flow.has_edge(next(iter(comp)), next(iter(comp))))]


def score_vendors(graph, recon_report: dict) -> list[VendorRisk]:
    """Score every taxpayer that issued at least one invoice."""
    g = graph
    recon_by_supplier: dict[str, dict] = {}
    for item in recon_report["items"]:
        recon_by_supplier.setdefault(item["supplierGstin"], {
            "issued": 0, "mismatched": 0, "mismatched_items": [],
        })
        entry = recon_by_supplier[item["supplierGstin"]]
        entry["issued"] += 1
        if item["status"] == "MISMATCHED":
            entry["mismatched"] += 1
            entry["mismatched_items"].append(item)

    flow = _taxpayer_flow_graph(g)
    cycle_components = _cycle_components(flow)
    cyc = set().union(*cycle_components) if cycle_components else set()

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

        unreported_ids = [
            inv for inv in issued_invoices
            if not any(
                g.edges[inv, w].get("type") == "REPORTED_IN"
                for w in g.successors(inv)
                if w.startswith("ReturnFiling:")
            )
        ]
        unreported = len(unreported_ids)

        # Liability vs paid via GSTR-1 -> Payment chain
        liability = Decimal("0")
        paid = Decimal("0")
        gstr1_ids: list[str] = []
        paid_ids: list[str] = []
        for ret in g.successors(n):
            if g.edges[n, ret].get("type") != "FILED":
                continue
            ret_data = g.nodes[ret]
            if ret_data.get("returnType") != "GSTR1":
                continue
            gstr1_ids.append(ret)
            liability += _d(ret_data.get("totalTaxLiability", 0))
            for pay in g.successors(ret):
                if g.edges[ret, pay].get("type") == "PAID_VIA":
                    paid_ids.append(pay)
                    paid += _d(g.nodes[pay].get("totalPaid", 0))

        shortfall = max(liability - paid, Decimal("0"))
        shortfall_ratio = float(shortfall / liability) if liability > 0 else 0.0

        stats = recon_by_supplier.get(gstin, {"issued": len(issued_invoices), "mismatched": 0, "mismatched_items": []})
        mismatch_rate = stats["mismatched"] / stats["issued"] if stats["issued"] else 0.0
        ghost_rate = unreported / len(issued_invoices) if issued_invoices else 0.0
        in_cycle = gstin in cyc
        cycle_comp = next((sorted(c) for c in cycle_components if gstin in c), None)

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
                taxLiability=_money(liability),
                taxPaid=_money(paid),
                shortfall=_money(shortfall),
                inCycle=in_cycle,
            ),
            evidence=_build_evidence(
                gstin=gstin, n=n, stats=stats, unreported_ids=unreported_ids,
                issued_invoices=issued_invoices, liability=liability, paid=paid,
                shortfall=shortfall, gstr1_ids=gstr1_ids, paid_ids=paid_ids,
                in_cycle=in_cycle, cycle_comp=cycle_comp,
                mismatch_rate=mismatch_rate, ghost_rate=ghost_rate,
            ),
        ))

    vendors.sort(key=lambda v: (-v.score, v.gstin))
    return vendors


_EVIDENCE_CAP = 20


def _build_evidence(*, gstin, n, stats, unreported_ids, issued_invoices,
                    liability, paid, shortfall, gstr1_ids, paid_ids,
                    in_cycle, cycle_comp, mismatch_rate, ghost_rate) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    if stats["mismatched"]:
        refs = [it.get("claimRef") for it in stats["mismatched_items"] if it.get("claimRef")]
        path = next((it.get("evidencePath") for it in stats["mismatched_items"] if it.get("evidencePath")), None)
        items.append(EvidenceItem(
            finding="MISMATCH", source="reconciliation",
            observed=f"{stats['mismatched']}/{stats['issued']}",
            ratio=round(mismatch_rate, 4),
            description=f"{stats['mismatched']} of {stats['issued']} ITC claims diverge from the supplier's books",
            itemRefs=refs[:_EVIDENCE_CAP],
            path=path,
        ))
    if unreported_ids:
        items.append(EvidenceItem(
            finding="GHOST_UNREPORTED", source="knowledge_graph",
            observed=f"{len(unreported_ids)}/{len(issued_invoices)}",
            ratio=round(ghost_rate, 4),
            description=f"{len(unreported_ids)} supplied invoices never appeared in any GSTR-1 return",
            itemRefs=[uid.split(":", 1)[-1] for uid in unreported_ids[:_EVIDENCE_CAP]],
            nodeIds=unreported_ids[:_EVIDENCE_CAP],
            path=[n, unreported_ids[0]],
        ))
    if shortfall > 0:
        items.append(EvidenceItem(
            finding="TAX_SHORTFALL", source="knowledge_graph",
            observed=_money(shortfall),
            liability=_money(liability), paid=_money(paid), shortfall=_money(shortfall),
            description=f"Filed liability {liability} against payments of {paid}",
            nodeIds=(gstr1_ids + sorted(set(paid_ids)))[:_EVIDENCE_CAP],
        ))
    if in_cycle and cycle_comp:
        items.append(EvidenceItem(
            finding="CYCLE_MEMBERSHIP", source="knowledge_graph",
            observed=f"cycle of {len(cycle_comp)}",
            description="Participates in a circular trading loop (strongly connected component)",
            cycleSize=len(cycle_comp), memberGstins=cycle_comp,
            nodeIds=[f"Taxpayer:{g}" for g in cycle_comp],
        ))
    return items
