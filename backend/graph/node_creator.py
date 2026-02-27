def upsert_taxpayer(tx, entity_ref_id: str, data: dict):
    query = """
    MERGE (t:Taxpayer {entity_ref_id: $entity_ref_id})
    SET t.gstin = $gstin,
        t.legal_name = $legal_name,
        t.trade_name = $trade_name,
        t.state_code = $state_code,
        t.registration_type = $registration_type,
        t.status = $status,
        t.registration_date = $registration_date,
        t.cancellation_date = $cancellation_date,
        t._is_stub = false
    """
    # Ensure all parameters exist with default None
    params = {
        "gstin": data.get("gstin"),
        "legal_name": data.get("legal_name"),
        "trade_name": data.get("trade_name"),
        "state_code": data.get("state_code"),
        "registration_type": data.get("registration_type"),
        "status": data.get("status"),
        "registration_date": data.get("registration_date"),
        "cancellation_date": data.get("cancellation_date")
    }
    tx.run(query, entity_ref_id=entity_ref_id, **params)

def upsert_invoice(tx, entity_ref_id: str, data: dict):
    query = """
    MERGE (i:Invoice {entity_ref_id: $entity_ref_id})
    SET i.invoice_number = $invoice_number,
        i.invoice_date = $invoice_date,
        i.financial_year = $financial_year,
        i.invoice_type = $invoice_type,
        i.document_type = $document_type,
        i.supplier_gstin = $supplier_gstin,
        i.recipient_gstin = $recipient_gstin,
        i.place_of_supply = $place_of_supply,
        i.supply_type = $supply_type,
        i.reverse_charge = $reverse_charge
    """
    params = {
        "invoice_number": data.get("invoice_number"),
        "invoice_date": data.get("invoice_date"),
        "financial_year": data.get("financial_year"),
        "invoice_type": data.get("invoice_type"),
        "document_type": data.get("document_type"),
        "supplier_gstin": data.get("supplier_gstin"),
        "recipient_gstin": data.get("recipient_gstin"),
        "place_of_supply": data.get("place_of_supply"),
        "supply_type": data.get("supply_type"),
        "reverse_charge": data.get("reverse_charge")
    }
    tx.run(query, entity_ref_id=entity_ref_id, **params)

def create_observation(tx, parent_entity_ref_id: str, source_record_id: str, 
                      source_context: dict, data: dict, lineage: dict, validation: dict):
    query = """
    MERGE (o:SourceObservation {source_record_id: $source_record_id})
    SET o.source_system = $source_system,
        o.reporter_role = $reporter_role,
        o.reporter_gstin = $reporter_gstin,
        o.reporting_period = $reporting_period,
        o.taxable_value = $taxable_value,
        o.igst_amount = $igst_amount,
        o.cgst_amount = $cgst_amount,
        o.sgst_amount = $sgst_amount,
        o.total_tax_amount = $total_tax_amount,
        o.total_invoice_value = $total_invoice_value,
        o.record_hash = $record_hash,
        o.batch_id = $batch_id,
        o.is_valid = $is_valid
        
    WITH o
    MATCH (i:Invoice {entity_ref_id: $parent_entity_ref_id})
    MERGE (i)-[:HAS_OBSERVATION]->(o)
    """
    
    # Extract only values we need for observation to avoid passing unnecessary objects
    params = {
        "source_record_id": source_record_id,
        "parent_entity_ref_id": parent_entity_ref_id,
        "source_system": source_context.get("source_system"),
        "reporter_role": source_context.get("reporter_role"),
        "reporter_gstin": source_context.get("reporter_gstin"),
        "reporting_period": source_context.get("reporting_period"),
        "taxable_value": float(data.get("taxable_value", 0)),
        "igst_amount": float(data.get("igst_amount", 0)),
        "cgst_amount": float(data.get("cgst_amount", 0)),
        "sgst_amount": float(data.get("sgst_amount", 0)),
        "total_tax_amount": float(data.get("total_tax_amount", 0)),
        "total_invoice_value": float(data.get("total_invoice_value", 0)),
        "record_hash": lineage.get("record_hash"),
        "batch_id": lineage.get("batch_id"),
        "is_valid": validation.get("is_valid", True)
    }
    tx.run(query, **params)

def upsert_return(tx, entity_ref_id: str, data: dict):
    query = """
    MERGE (r:Return {entity_ref_id: $entity_ref_id})
    SET r.gstin = $gstin,
        r.return_type = $return_type,
        r.return_period = $return_period,
        r.filing_date = $filing_date,
        r.filing_status = $filing_status,
        r.arn = $arn,
        r.total_records = $total_records,
        r.aggregate_taxable_value = $aggregate_taxable_value,
        r.aggregate_igst = $aggregate_igst,
        r.aggregate_cgst = $aggregate_cgst,
        r.aggregate_sgst = $aggregate_sgst,
        r.aggregate_cess = $aggregate_cess
    """
    
    processed_data = {
        "gstin": data.get("gstin"),
        "return_type": data.get("return_type"),
        "return_period": data.get("return_period"),
        "filing_date": data.get("filing_date"),
        "filing_status": data.get("filing_status"),
        "arn": data.get("arn"),
        "total_records": data.get("total_records"),
        "aggregate_taxable_value": float(data.get("aggregate_taxable_value", 0)) if data.get("aggregate_taxable_value") else None,
        "aggregate_igst": float(data.get("aggregate_igst", 0)) if data.get("aggregate_igst") else None,
        "aggregate_cgst": float(data.get("aggregate_cgst", 0)) if data.get("aggregate_cgst") else None,
        "aggregate_sgst": float(data.get("aggregate_sgst", 0)) if data.get("aggregate_sgst") else None,
        "aggregate_cess": float(data.get("aggregate_cess", 0)) if data.get("aggregate_cess") else None
    }
    tx.run(query, entity_ref_id=entity_ref_id, **processed_data)

def upsert_payment(tx, entity_ref_id: str, data: dict):
    query = """
    MERGE (p:Payment {entity_ref_id: $entity_ref_id})
    SET p.gstin = $gstin,
        p.challan_number = $challan_number,
        p.payment_date = $payment_date,
        p.tax_period = $tax_period,
        p.payment_mode = $payment_mode,
        p.igst_paid = $igst_paid,
        p.cgst_paid = $cgst_paid,
        p.sgst_paid = $sgst_paid,
        p.cess_paid = $cess_paid,
        p.interest_paid = $interest_paid,
        p.penalty_paid = $penalty_paid,
        p.total_paid = $total_paid,
        p.payment_status = $payment_status,
        p.bank_reference = $bank_reference
    """
    
    processed_data = {
        "gstin": data.get("gstin"),
        "challan_number": data.get("challan_number"),
        "payment_date": data.get("payment_date"),
        "tax_period": data.get("tax_period"),
        "payment_mode": data.get("payment_mode"),
        "igst_paid": float(data.get("igst_paid", 0)) if data.get("igst_paid") is not None else None,
        "cgst_paid": float(data.get("cgst_paid", 0)) if data.get("cgst_paid") is not None else None,
        "sgst_paid": float(data.get("sgst_paid", 0)) if data.get("sgst_paid") is not None else None,
        "cess_paid": float(data.get("cess_paid", 0)) if data.get("cess_paid") is not None else None,
        "interest_paid": float(data.get("interest_paid", 0)) if data.get("interest_paid") is not None else None,
        "penalty_paid": float(data.get("penalty_paid", 0)) if data.get("penalty_paid") is not None else None,
        "total_paid": float(data.get("total_paid", 0)) if data.get("total_paid") is not None else None,
        "payment_status": data.get("payment_status"),
        "bank_reference": data.get("bank_reference")
    }
    tx.run(query, entity_ref_id=entity_ref_id, **processed_data)

def upsert_irn(tx, entity_ref_id: str, data: dict):
    query = """
    MERGE (n:IRN {entity_ref_id: $entity_ref_id})
    SET n.irn = $irn,
        n.ack_number = $ack_number,
        n.ack_date = $ack_date,
        n.generation_datetime = $generation_datetime,
        n.irn_status = $irn_status,
        n.supplier_gstin = $supplier_gstin,
        n.recipient_gstin = $recipient_gstin,
        n.invoice_number = $invoice_number,
        n.original_invoice_number = $original_invoice_number,
        n.invoice_date = $invoice_date,
        n.document_type = $document_type,
        n.taxable_value = $taxable_value,
        n.igst_amount = $igst_amount,
        n.cgst_amount = $cgst_amount,
        n.sgst_amount = $sgst_amount,
        n.cess_amount = $cess_amount,
        n.total_invoice_value = $total_invoice_value,
        n.signed_qr_code = $signed_qr_code,
        n.cancellation_date = $cancellation_date,
        n.cancellation_reason = $cancellation_reason
    """
    
    processed_data = {
        "irn": data.get("irn"),
        "ack_number": data.get("ack_number"),
        "ack_date": data.get("ack_date"),
        "generation_datetime": data.get("generation_datetime") if isinstance(data.get("generation_datetime"), str) else (data.get("generation_datetime").isoformat() if data.get("generation_datetime") else None),
        "irn_status": data.get("irn_status"),
        "supplier_gstin": data.get("supplier_gstin"),
        "recipient_gstin": data.get("recipient_gstin"),
        "invoice_number": data.get("invoice_number"),
        "original_invoice_number": data.get("original_invoice_number"),
        "invoice_date": data.get("invoice_date"),
        "document_type": data.get("document_type"),
        "taxable_value": float(data.get("taxable_value", 0)) if data.get("taxable_value") is not None else None,
        "igst_amount": float(data.get("igst_amount", 0)) if data.get("igst_amount") is not None else None,
        "cgst_amount": float(data.get("cgst_amount", 0)) if data.get("cgst_amount") is not None else None,
        "sgst_amount": float(data.get("sgst_amount", 0)) if data.get("sgst_amount") is not None else None,
        "cess_amount": float(data.get("cess_amount", 0)) if data.get("cess_amount") is not None else None,
        "total_invoice_value": float(data.get("total_invoice_value", 0)) if data.get("total_invoice_value") is not None else None,
        "signed_qr_code": data.get("signed_qr_code"),
        "cancellation_date": data.get("cancellation_date"),
        "cancellation_reason": data.get("cancellation_reason")
    }
        
    tx.run(query, entity_ref_id=entity_ref_id, **processed_data)

def create_stub_taxpayer(tx, entity_ref_id: str, gstin: str):
    query = """
    MERGE (t:Taxpayer {entity_ref_id: $entity_ref_id})
    ON CREATE SET t.gstin = $gstin,
                 t._is_stub = true,
                 t._stub_reason = "Referenced but not in source data",
                 t.legal_name = "UNKNOWN",
                 t.status = "UNKNOWN"
    """
    tx.run(query, entity_ref_id=entity_ref_id, gstin=gstin)
