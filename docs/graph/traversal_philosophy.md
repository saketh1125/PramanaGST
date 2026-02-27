# Traversal Philosophy

PramanaGST Reconciles via **Graph Traversal**, not table joins.

## Concept: "The Golden Path"
A perfectly compliant B2B transaction creates an unbroken path from the Supplier to the Government.

**Path Signature:**
`Taxpayer(Supplier) -[SUPPLIED]-> Invoice -[REPORTED_IN]-> ReturnFiling(GSTR1) -[PAID_VIA]-> Payment`

If the Buyer claims ITC on this `Invoice`, the `Invoice` must exist on the Golden Path above.

## Concept: "Broken Paths"
The Reconciliation Engine searches primarily for broken paths — nodes that lack the required downstream relationships.

**Example: Missing Payment (Tax Evasion Risk)**
```cypher
MATCH (supplier:Taxpayer)-[:SUPPLIED]->(inv:Invoice)-[:REPORTED_IN]->(r1:ReturnFiling)
WHERE NOT (r1)-[:PAID_VIA]->(:Payment {paymentStatus: "PAID"})
RETURN inv, supplier "High Risk: Invoice reported but tax unpaid"
```

**Example: Ghost Invoices (Fraud Risk)**
```cypher
MATCH (buyer:Taxpayer)-[:RECEIVED]->(inv:Invoice)
WHERE NOT ()-[:SUPPLIED]->(inv)
RETURN inv "Critical Risk: Ghost seller detected"
```
