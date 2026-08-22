"""
Graph projection — the hybrid seam between Neo4j and NetworkX.

Two producers, one graph shape:
  - build_from_batch(): offline projection straight from a Contract-1 batch
    (dev/demo without a live DB).
  - project_from_neo4j(): rebuild the same NetworkX graph from persisted data.

Analytics layers must only consume nx.DiGraph objects produced here.
"""

import os

import networkx as nx

# Neo4j label -> unique identifying property
_KEY_BY_LABEL = {
    "Taxpayer": "gstin",
    "Invoice": "refId",
    "ReturnFiling": "returnId",
    "Payment": "paymentId",
    "IRN": "irn",
}


def _key(label: str, props: dict) -> str:
    return f"{label}:{props[_KEY_BY_LABEL[label]]}"


def build_from_batch(batch: dict) -> nx.DiGraph:
    """Project Contract-1 batch entities into an in-memory DiGraph.

    SOURCE_OBSERVATION entities become CLAIMED_IN edge properties on
    Invoice -> GSTR2B Return edges (mirrors loader.py semantics).
    """
    g = nx.DiGraph()
    invoices = {}
    returns = {}

    for e in batch["entities"]:
        et, d = e["entity_type"], e["data"]
        if et == "TAXPAYER":
            g.add_node(_key("Taxpayer", d), label="Taxpayer", **d)
        elif et == "INVOICE":
            invoices[e["ref_id"]] = d
            g.add_node(_key("Invoice", d), label="Invoice", **d)
        elif et == "RETURN":
            returns[d["returnId"]] = d
            g.add_node(f"ReturnFiling:{d['returnId']}", label="ReturnFiling", **d)
        elif et == "PAYMENT":
            g.add_node(_key("Payment", d), label="Payment", **d)
        elif et == "IRN":
            g.add_node(_key("IRN", d), label="IRN", **d)

    for inv in invoices.values():
        ik = _key("Invoice", inv)
        sk = f"Taxpayer:{inv['supplierGstin']}"
        if sk in g:
            g.add_edge(sk, ik, type="SUPPLIED")
        rk = f"Taxpayer:{inv.get('recipientGstin')}" if inv.get("recipientGstin") else None
        if rk and rk in g:
            g.add_edge(rk, ik, type="RECEIVED")
        g1k = f"ReturnFiling:GSTR1-{inv['supplierGstin']}-{inv['filingPeriod']}"
        if g1k in g:
            g.add_edge(ik, g1k, type="REPORTED_IN")
        irn = inv.get("irn")
        if irn and _key("IRN", {"irn": irn}) in g:
            g.add_edge(ik, f"IRN:{irn}", type="REGISTERED")

    for rid, ret in returns.items():
        tk = f"Taxpayer:{ret['gstin']}"
        if tk in g:
            g.add_edge(tk, f"ReturnFiling:{rid}", type="FILED")
        if ret["returnType"] == "GSTR1":
            pk = _key("Payment", {
                "paymentId": f"PMT-{ret['gstin']}-{ret['returnPeriod']}",
                "gstin": ret["gstin"], "returnPeriod": ret["returnPeriod"],
            })
            if pk in g:
                g.add_edge(f"ReturnFiling:{rid}", pk, type="PAID_VIA")

    for e in batch["entities"]:
        if e["entity_type"] != "SOURCE_OBSERVATION":
            continue
        o = e["data"]
        # locate the invoice node by number + recipient
        target = None
        for inv_ref, d in invoices.items():
            if d["invoiceNumber"] == o["invoiceNumber"] and d.get("recipientGstin") == o["recipientGstin"]:
                target = inv_ref
                break
        if target is None:
            continue
        g2bk = f"ReturnFiling:GSTR2B-{o['recipientGstin']}-{o['claimPeriod']}"
        if g2bk in g:
            g.add_edge(f"Invoice:{target}", g2bk, type="CLAIMED_IN",
                       itcClaimed=o["itcClaimed"], claimPeriod=o["claimPeriod"])

    return g


def project_from_neo4j(uri=None, user=None, password=None) -> nx.DiGraph:
    """Rebuild the NetworkX projection from the persisted Neo4j graph."""
    from neo4j import GraphDatabase

    uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = user or os.environ.get("NEO4J_USER", "neo4j")
    password = password or os.environ.get("NEO4J_PASSWORD", "pramanagst")

    g = nx.DiGraph()
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (a)-[r]->(b)
                RETURN labels(a)[0] AS la, properties(a) AS pa,
                       type(r) AS rel, properties(r) AS pr,
                       labels(b)[0] AS lb, properties(b) AS pb
                """
            )
            for rec in result:
                la, pa, rel, pr, lb, pb = (
                    rec["la"], rec["pa"], rec["rel"], dict(rec["pr"]), rec["lb"], rec["pb"],
                )
                ak, bk = _key(la, pa), _key(lb, pb)
                if ak not in g:
                    g.add_node(ak, label=la, **pa)
                if bk not in g:
                    g.add_node(bk, label=lb, **pb)
                g.add_edge(ak, bk, type=rel, **pr)
    finally:
        driver.close()
    return g
