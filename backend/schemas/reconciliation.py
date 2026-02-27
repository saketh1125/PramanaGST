from pydantic import BaseModel
from typing import Optional, List

class MismatchDetail(BaseModel):
    field: str
    source_a: str
    value_a: str
    source_b: str
    value_b: str
    difference: str

class ReconciliationResult(BaseModel):
    entity_ref_id: str
    invoice_number: str
    supplier_gstin: str
    recipient_gstin: Optional[str]
    invoice_date: str
    financial_year: str
    match_status: str
    sources_present: List[str]
    sources_missing: List[str]
    mismatches: List[MismatchDetail]
    taxable_value_by_source: dict
    tax_amount_by_source: dict
    itc_eligible: bool
    itc_ineligibility_reasons: List[str]
    confidence_score: float

class ReconciliationSummary(BaseModel):
    total_invoices: int
    full_match: int
    partial_match: int
    missing_in_gstr1: int
    missing_in_gstr2b: int
    missing_in_pr: int
    value_mismatch: int
    total_taxable_value: float
    total_tax_at_risk: float
    match_rate_percent: float
