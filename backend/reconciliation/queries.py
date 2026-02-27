"""
Cypher query templates for the Reconciliation Engine.
Each query is a string constant intended to be run against Neo4j.
All queries use MERGE/MATCH patterns consistent with our graph schema.
"""

# Q1: Get all invoices with all their linked SourceObservation nodes
# Used as a base read for the reconciliation pass
Q1_ALL_INVOICES_WITH_OBSERVATIONS = """
MATCH (i:Invoice)-[:HAS_OBSERVATION]->(o:SourceObservation)
OPTIONAL MATCH (i)-[:ISSUED_BY]->(supplier:Taxpayer)
OPTIONAL MATCH (i)-[:RECEIVED_BY]->(buyer:Taxpayer)
RETURN i.entity_ref_id          AS entity_ref_id,
       i.invoice_number          AS invoice_number,
       i.invoice_date            AS invoice_date,
       i.financial_year          AS financial_year,
       i.supplier_gstin          AS supplier_gstin,
       i.recipient_gstin         AS recipient_gstin,
       i.invoice_type            AS invoice_type,
       supplier.legal_name       AS supplier_name,
       buyer.legal_name          AS buyer_name,
       collect({
         source_system:       o.source_system,
         reporter_role:       o.reporter_role,
         reporter_gstin:      o.reporter_gstin,
         taxable_value:       o.taxable_value,
         igst_amount:         o.igst_amount,
         cgst_amount:         o.cgst_amount,
         sgst_amount:         o.sgst_amount,
         total_tax_amount:    o.total_tax_amount,
         total_invoice_value: o.total_invoice_value,
         reporting_period:    o.reporting_period,
         source_record_id:    o.source_record_id
       }) AS observations
"""

# Q2: Invoices present in GSTR-1 but absent from GSTR-2B
Q2_MISSING_IN_GSTR2B = """
MATCH (i:Invoice)-[:HAS_OBSERVATION]->(o:SourceObservation)
WHERE o.source_system = 'GSTR1'
AND NOT EXISTS {
  MATCH (i)-[:HAS_OBSERVATION]->(o2:SourceObservation)
  WHERE o2.source_system = 'GSTR2B'
}
RETURN i.entity_ref_id    AS entity_ref_id,
       i.invoice_number   AS invoice_number,
       i.supplier_gstin   AS supplier_gstin,
       i.recipient_gstin  AS recipient_gstin,
       o.taxable_value    AS taxable_value,
       o.total_tax_amount AS total_tax_amount
"""

# Q3: Invoices where GSTR-1 and GSTR-2B taxable/tax values diverge beyond tolerance
Q3_VALUE_MISMATCHES = """
MATCH (i:Invoice)-[:HAS_OBSERVATION]->(o1:SourceObservation {source_system: 'GSTR1'})
MATCH (i)-[:HAS_OBSERVATION]->(o2:SourceObservation {source_system: 'GSTR2B'})
WHERE abs(o1.taxable_value    - o2.taxable_value)    > 1.0
   OR abs(o1.total_tax_amount - o2.total_tax_amount) > 1.0
RETURN i.entity_ref_id                                    AS entity_ref_id,
       i.invoice_number                                   AS invoice_number,
       o1.taxable_value                                   AS gstr1_taxable,
       o2.taxable_value                                   AS gstr2b_taxable,
       o1.total_tax_amount                                AS gstr1_tax,
       o2.total_tax_amount                                AS gstr2b_tax,
       abs(o1.taxable_value    - o2.taxable_value)        AS taxable_diff,
       abs(o1.total_tax_amount - o2.total_tax_amount)     AS tax_diff
"""

# Q4: Full reconciliation chain — all B2B invoices with their observation source sets
# Primary driver for matcher.py
Q4_FULL_RECONCILIATION = """
MATCH (i:Invoice)
WHERE i.invoice_type = 'B2B'
OPTIONAL MATCH (i)-[:HAS_OBSERVATION]->(o:SourceObservation)
OPTIONAL MATCH (i)-[:ISSUED_BY]->(supplier:Taxpayer)
OPTIONAL MATCH (i)-[:RECEIVED_BY]->(buyer:Taxpayer)
WITH i, supplier, buyer,
     collect(o.source_system) AS sources,
     collect({
       source:       o.source_system,
       taxable:      o.taxable_value,
       tax:          o.total_tax_amount,
       igst:         o.igst_amount,
       cgst:         o.cgst_amount,
       sgst:         o.sgst_amount,
       period:       o.reporting_period,
       record_id:    o.source_record_id
     }) AS observations
RETURN i.entity_ref_id     AS entity_ref_id,
       i.invoice_number    AS invoice_number,
       i.invoice_date      AS invoice_date,
       i.financial_year    AS financial_year,
       i.supplier_gstin    AS supplier_gstin,
       i.recipient_gstin   AS recipient_gstin,
       i.invoice_type      AS invoice_type,
       supplier.legal_name AS supplier_name,
       supplier.status     AS supplier_status,
       buyer.legal_name    AS buyer_name,
       sources,
       size(observations)  AS observation_count,
       observations
ORDER BY size(sources) ASC
"""

# Q5: ITC eligibility check — multi-hop path through supplier status, IRN, GSTR-1 filing
Q5_ITC_ELIGIBILITY = """
MATCH (i:Invoice {entity_ref_id: $entity_ref_id})-[:ISSUED_BY]->(supplier:Taxpayer)
WHERE i.invoice_type = 'B2B'
OPTIONAL MATCH (i)-[:HAS_OBSERVATION]->(o_gstr2b:SourceObservation {source_system: 'GSTR2B'})
OPTIONAL MATCH (i)-[:LINKED_TO]->(irn:IRN)
OPTIONAL MATCH (supplier)-[:FILED]->(ret:Return {return_type: 'GSTR1'})
RETURN i.entity_ref_id                AS entity_ref_id,
       i.invoice_number               AS invoice_number,
       supplier.status                AS supplier_status,
       o_gstr2b IS NOT NULL           AS in_gstr2b,
       irn.irn_status                 AS irn_status,
       ret.filing_status              AS supplier_filing_status,
       ret.return_period              AS return_period,
       CASE
         WHEN o_gstr2b IS NULL              THEN false
         WHEN supplier.status = 'CANCELLED' THEN false
         WHEN irn.irn_status = 'CANCELLED'  THEN false
         ELSE true
       END AS itc_eligible
"""

# Q6: Detect circular trading — 3-hop cycles among taxpayers via invoices
Q6_CIRCULAR_TRADING = """
MATCH path = (t1:Taxpayer)<-[:ISSUED_BY]-(i1:Invoice)-[:RECEIVED_BY]->(t2:Taxpayer)
             <-[:ISSUED_BY]-(i2:Invoice)-[:RECEIVED_BY]->(t3:Taxpayer)
             <-[:ISSUED_BY]-(i3:Invoice)-[:RECEIVED_BY]->(t1)
WHERE t1 <> t2 AND t2 <> t3 AND t1 <> t3
RETURN t1.gstin          AS gstin_a,
       t2.gstin          AS gstin_b,
       t3.gstin          AS gstin_c,
       t1.legal_name     AS name_a,
       t2.legal_name     AS name_b,
       t3.legal_name     AS name_c,
       i1.invoice_number AS inv_ab,
       i2.invoice_number AS inv_bc,
       i3.invoice_number AS inv_ca
"""

# Q_STUB: Find all stub (synthetically created) nodes for auditing dangling refs
Q_STUB_NODES = """
MATCH (n {_is_stub: true})
RETURN labels(n)[0] AS label,
       n.entity_ref_id AS id,
       n._stub_reason  AS reason
"""

# Q_GRAPH_SUMMARY: Node and relationship counts for health check
Q_GRAPH_SUMMARY = """
MATCH (n)
RETURN labels(n)[0] AS label, count(n) AS count
ORDER BY count DESC
"""
