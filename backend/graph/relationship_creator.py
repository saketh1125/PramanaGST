def create_issued_by(tx, invoice_ref_id: str, supplier_ref_id: str):
    query = """
    MATCH (i:Invoice {entity_ref_id: $invoice_ref_id})
    MATCH (t:Taxpayer {entity_ref_id: $supplier_ref_id})
    MERGE (i)-[:ISSUED_BY]->(t)
    """
    tx.run(query, invoice_ref_id=invoice_ref_id, supplier_ref_id=supplier_ref_id)


def create_received_by(tx, invoice_ref_id: str, recipient_ref_id: str, recipient_gstin: str):
    if not recipient_ref_id:
        return
        
    query = """
    MATCH (i:Invoice {entity_ref_id: $invoice_ref_id})
    MERGE (t:Taxpayer {entity_ref_id: $recipient_ref_id})
    ON CREATE SET t._is_stub = true, 
                  t.gstin = $recipient_gstin,
                  t._stub_reason = "Referenced as buyer but not in taxpayer source",
                  t.legal_name = "UNKNOWN",
                  t.status = "UNKNOWN"
    MERGE (i)-[:RECEIVED_BY]->(t)
    """
    tx.run(query, invoice_ref_id=invoice_ref_id, 
           recipient_ref_id=recipient_ref_id, 
           recipient_gstin=recipient_gstin)


def create_reported_in(tx, invoice_ref_id: str, return_ref_id: str, 
                       reporter_gstin: str, return_period: str, source_context: dict, data: dict,
                       return_type: str = "UNKNOWN"):
    query = """
    MATCH (i:Invoice {entity_ref_id: $invoice_ref_id})
    MERGE (r:Return {entity_ref_id: $return_ref_id})
    ON CREATE SET r.return_type = $return_type,
                 r.return_period = $return_period,
                 r.gstin = $reporter_gstin,
                 r.filing_status = "UNKNOWN"
    MERGE (i)-[rel:REPORTED_IN]->(r)
    SET rel.source_system = $source_system,
        rel.reporter_role = $reporter_role,
        rel.source_record_id = $source_record_id,
        rel.taxable_value = $taxable_value,
        rel.total_tax_amount = $total_tax_amount
    """
    tx.run(query, 
           invoice_ref_id=invoice_ref_id,
           return_ref_id=return_ref_id,
           return_type=return_type,
           return_period=return_period,
           reporter_gstin=reporter_gstin,
           source_system=source_context.get("source_system"),
           reporter_role=source_context.get("reporter_role"),
           source_record_id=source_context.get("source_record_id"), # Often same as observation level
           taxable_value=float(data.get("taxable_value", 0)),
           total_tax_amount=float(data.get("total_tax_amount", 0)))


def create_filed_by(tx, taxpayer_ref_id: str, return_ref_id: str, data: dict):
    query = """
    MATCH (t:Taxpayer {entity_ref_id: $taxpayer_ref_id})
    MATCH (r:Return {entity_ref_id: $return_ref_id})
    MERGE (t)-[rel:FILED]->(r)
    SET rel.filing_date = $filing_date,
        rel.filing_status = $filing_status
    """
    filing_date = data.get("filing_date")
    # Convert date to string format for neo4j properties
    if filing_date:
        filing_date = filing_date.isoformat() if hasattr(filing_date, 'isoformat') else str(filing_date)
        
    tx.run(query, 
           taxpayer_ref_id=taxpayer_ref_id, 
           return_ref_id=return_ref_id,
           filing_date=filing_date,
           filing_status=data.get("filing_status"))


def create_paid_tax_in(tx, taxpayer_ref_id: str, payment_ref_id: str, data: dict):
    query = """
    MATCH (t:Taxpayer {entity_ref_id: $taxpayer_ref_id})
    MATCH (p:Payment {entity_ref_id: $payment_ref_id})
    MERGE (t)-[rel:PAID_TAX_IN]->(p)
    SET rel.tax_period = $tax_period,
        rel.payment_date = $payment_date
    """
    payment_date = data.get("payment_date")
    if payment_date:
        payment_date = payment_date.isoformat() if hasattr(payment_date, 'isoformat') else str(payment_date)
        
    tx.run(query, 
           taxpayer_ref_id=taxpayer_ref_id, 
           payment_ref_id=payment_ref_id,
           tax_period=data.get("tax_period"),
           payment_date=payment_date)


def create_linked_to_irn(tx, invoice_ref_id: str, irn_ref_id: str, data: dict):
    query = """
    MATCH (i:Invoice {entity_ref_id: $invoice_ref_id})
    MATCH (n:IRN {entity_ref_id: $irn_ref_id})
    MERGE (i)-[rel:LINKED_TO]->(n)
    SET rel.ack_number = $ack_number,
        rel.ack_date = $ack_date,
        rel.irn_status = $irn_status
    """
    ack_date = data.get("ack_date")
    if ack_date:
        ack_date = ack_date.isoformat() if hasattr(ack_date, 'isoformat') else str(ack_date)
        
    tx.run(query, 
           invoice_ref_id=invoice_ref_id, 
           irn_ref_id=irn_ref_id,
           ack_number=data.get("ack_number"),
           ack_date=ack_date,
           irn_status=data.get("irn_status"))


def create_recorded_in(tx, invoice_ref_id: str, buyer_ref_id: str, source_context: dict, data: dict):
    # This relationship tracks purchase register records
    query = """
    MATCH (i:Invoice {entity_ref_id: $invoice_ref_id})
    MATCH (t:Taxpayer {entity_ref_id: $buyer_ref_id})
    MERGE (i)-[rel:RECORDED_IN]->(t)
    SET rel.source_record_id = $source_record_id,
        rel.reporting_period = $reporting_period,
        rel.taxable_value = $taxable_value,
        rel.total_tax_amount = $total_tax_amount
    """
    tx.run(query, 
           invoice_ref_id=invoice_ref_id, 
           buyer_ref_id=buyer_ref_id,
           source_record_id=source_context.get("source_record_id"), # Passed explicitly or extracted outside
           reporting_period=source_context.get("reporting_period"),
           taxable_value=float(data.get("taxable_value", 0)),
           total_tax_amount=float(data.get("total_tax_amount", 0)))


def create_adjusts(tx, cn_ref_id: str, original_invoice_ref_id: str, data: dict):
    query = """
    MATCH (cn:Invoice {entity_ref_id: $cn_ref_id})
    MATCH (orig:Invoice {entity_ref_id: $original_invoice_ref_id})
    MERGE (cn)-[rel:ADJUSTS]->(orig)
    SET rel.document_type = $document_type,
        rel.adjustment_date = $adjustment_date
    """
    adj_date = data.get("invoice_date") # Credit Note date
    if adj_date:
         adj_date = adj_date.isoformat() if hasattr(adj_date, 'isoformat') else str(adj_date)
         
    tx.run(query, 
           cn_ref_id=cn_ref_id, 
           original_invoice_ref_id=original_invoice_ref_id,
           document_type=data.get("document_type"),
           adjustment_date=adj_date)
