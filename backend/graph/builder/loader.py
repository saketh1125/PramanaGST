"""
Neo4j loader — persist Contract-1 batch entities and relationships.

Writes are MERGE-based (idempotent): re-running a batch updates in place.
Neo4j is the source of truth; NetworkX projections are derived (see projection.py).
"""

import os

from neo4j import GraphDatabase

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schema", "neo4j_schema.cypher")

# entity_type -> (label, unique-key property, property whitelist)
_NODE_SPECS = {
    "TAXPAYER": ("Taxpayer", "gstin",
                 ["gstin", "legalName", "registrationType", "registrationStatus",
                  "registrationDate", "stateCode", "pan"]),
    "INVOICE": ("Invoice", "refId",
                ["refId", "invoiceNumber", "invoiceDate", "invoiceType", "invoiceStatus",
                 "supplyType", "documentType", "supplierGstin", "recipientGstin",
                 "taxableValue", "igstAmount", "cgstAmount", "sgstAmount", "cessAmount",
                 "totalValue", "placeOfSupply", "reverseCharge", "irn", "filingPeriod"]),
    "RETURN": ("ReturnFiling", "returnId",
               ["returnId", "gstin", "returnType", "returnPeriod", "filingDate",
                "filingStatus", "totalTaxableValue", "totalIgst", "totalCgst",
                "totalSgst", "totalCess", "totalTaxLiability",
                "itcClaimedIgst", "itcClaimedCgst", "itcClaimedSgst", "itcClaimedCess"]),
    "PAYMENT": ("Payment", "paymentId",
                ["paymentId", "gstin", "returnPeriod", "paymentDate", "paymentMode",
                 "paymentStatus", "igstPaid", "cgstPaid", "sgstPaid", "cessPaid", "totalPaid"]),
    "IRN": ("IRN", "irn",
            ["irn", "irnDate", "irnStatus", "invoiceNumber", "supplierGstin", "documentType"]),
}

_EDGE_QUERIES = {
    # Taxpayer -> Invoice
    "SUPPLIED": """
        MATCH (t:Taxpayer {gstin: $supplierGstin}), (i:Invoice {refId: $refId})
        MERGE (t)-[:SUPPLIED]->(i)""",
    "RECEIVED": """
        MATCH (t:Taxpayer {gstin: $recipientGstin}), (i:Invoice {refId: $refId})
        MERGE (t)-[:RECEIVED]->(i)""",
    # Taxpayer -> ReturnFiling
    "FILED": """
        MATCH (t:Taxpayer {gstin: $gstin}), (r:ReturnFiling {returnId: $returnId})
        MERGE (t)-[:FILED]->(r)""",
    # Invoice -> GSTR-1 return it was reported in
    "REPORTED_IN_GSTR1": """
        MATCH (i:Invoice {refId: $invoiceRef}), (r:ReturnFiling {returnId: $returnId})
        MERGE (i)-[:REPORTED_IN]->(r)""",
    # Invoice -> GSTR-2B claim edge carrying claimed amount
    "CLAIMED_IN": """
        MATCH (i:Invoice {refId: $invoiceRef}), (r:ReturnFiling {returnId: $returnId})
        MERGE (i)-[c:CLAIMED_IN]->(r)
        SET c.itcClaimed = $itcClaimed, c.claimPeriod = $claimPeriod""",
    # ReturnFiling -> Payment
    "PAID_VIA": """
        MATCH (r:ReturnFiling {returnId: $returnId}), (p:Payment {paymentId: $paymentId})
        MERGE (r)-[:PAID_VIA]->(p)""",
    # Invoice -> IRN
    "REGISTERED": """
        MATCH (i:Invoice {refId: $invoiceRef}), (n:IRN {irn: $irn})
        MERGE (i)-[:REGISTERED]->(n)""",
}


class Neo4jLoader:
    """Loads a Contract-1 batch into Neo4j."""

    def __init__(self, uri=None, user=None, password=None):
        self.uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD", "pramanagst")
        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver

    def close(self):
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def apply_schema(self):
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            statements = [s.strip() for s in f.read().split(";") if s.strip() and not s.strip().startswith("//")]
        with self.driver.session() as session:
            for stmt in statements:
                session.run(stmt)

    def _node_props(self, entity_type: str, data: dict) -> dict:
        label, key, props = _NODE_SPECS[entity_type]
        clean = {}
        for p in props:
            v = data.get(p)
            if v is not None:
                clean[p] = v
        return {"label": label, "key": key, "props": clean}

    def load_batch(self, batch: dict) -> dict:
        """Write all entities + relationships. Returns counts."""
        counts = {"nodes": 0, "edges": 0}
        with self.driver.session() as session:
            session.execute_write(self._write_nodes, batch["entities"], counts)
            session.execute_write(self._write_edges, batch["entities"], counts)
        return counts

    @staticmethod
    def _write_nodes(tx, entities, counts):
        for e in entities:
            et = e["entity_type"]
            if et not in _NODE_SPECS:
                continue  # SOURCE_OBSERVATION becomes an edge, not a node
            spec = Neo4jLoader._node_props(et, e["data"])
            tx.run(
                f"MERGE (n:{spec['label']} {{{spec['key']}: $key}}) "
                f"SET n += $props, n.contractVersion = '1.0.0'",
                key=e["data"][spec["key"]], props=spec["props"],
            )
            counts["nodes"] += 1

    @staticmethod
    def _write_edges(tx, entities, counts):
        invoices = [e for e in entities if e["entity_type"] == "INVOICE"]
        returns = {e["data"]["returnId"]: e["data"] for e in entities if e["entity_type"] == "RETURN"}
        observations = [e for e in entities if e["entity_type"] == "SOURCE_OBSERVATION"]

        def run(query, **params):
            tx.run(query, **params)
            counts["edges"] += 1

        for inv in invoices:
            d = inv["data"]
            ref = d["refId"]
            run(_EDGE_QUERIES["SUPPLIED"], supplierGstin=d["supplierGstin"], refId=ref)
            if d.get("recipientGstin"):
                run(_EDGE_QUERIES["RECEIVED"], recipientGstin=d["recipientGstin"], refId=ref)
            g1_return = f"GSTR1-{d['supplierGstin']}-{d['filingPeriod']}"
            if g1_return in returns:
                run(_EDGE_QUERIES["REPORTED_IN_GSTR1"], invoiceRef=ref, returnId=g1_return)
            if d.get("irn"):
                run(_EDGE_QUERIES["REGISTERED"], invoiceRef=ref, irn=d["irn"])

        for ret in returns.values():
            run(_EDGE_QUERIES["FILED"], gstin=ret["gstin"], returnId=ret["returnId"])
            payment_id = f"PMT-{ret['gstin']}-{ret['returnPeriod']}"
            run(_EDGE_QUERIES["PAID_VIA"], returnId=ret["returnId"], paymentId=payment_id)

        for obs in observations:
            o = obs["data"]
            inv_num = o["invoiceNumber"]
            candidates = [
                i for i in invoices
                if i["data"]["invoiceNumber"] == inv_num
                and i["data"].get("recipientGstin") == o["recipientGstin"]
            ]
            if not candidates:
                continue
            g2b_return = f"GSTR2B-{o['recipientGstin']}-{o['claimPeriod']}"
            if g2b_return not in returns:
                continue
            run(_EDGE_QUERIES["CLAIMED_IN"], invoiceRef=candidates[0]["refId"],
                returnId=g2b_return, itcClaimed=o["itcClaimed"], claimPeriod=o["claimPeriod"])
