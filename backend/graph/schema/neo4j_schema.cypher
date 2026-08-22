// PramanaGST Knowledge Graph schema — Contract v1.0.0
// Idempotent; safe to re-run on every deploy.

CREATE CONSTRAINT taxpayer_gstin IF NOT EXISTS
FOR (t:Taxpayer) REQUIRE t.gstin IS UNIQUE;

CREATE CONSTRAINT invoice_ref IF NOT EXISTS
FOR (i:Invoice) REQUIRE i.refId IS UNIQUE;

CREATE CONSTRAINT return_ref IF NOT EXISTS
FOR (r:ReturnFiling) REQUIRE r.returnId IS UNIQUE;

CREATE CONSTRAINT payment_ref IF NOT EXISTS
FOR (p:Payment) REQUIRE p.paymentId IS UNIQUE;

CREATE CONSTRAINT irn_hash IF NOT EXISTS
FOR (n:IRN) REQUIRE n.irn IS UNIQUE;

CREATE INDEX invoice_number_idx IF NOT EXISTS
FOR (i:Invoice) ON (i.invoiceNumber);
