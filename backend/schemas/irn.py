from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date, datetime
from decimal import Decimal

class IRNData(BaseModel):
    irn: str = Field(..., min_length=64, max_length=64)
    ack_number: str
    ack_date: date
    generation_datetime: datetime
    irn_status: Literal["ACTIVE", "CANCELLED"]
    supplier_gstin: str = Field(..., pattern=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
    recipient_gstin: str = Field(..., pattern=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
    invoice_number: str = Field(..., min_length=1)
    original_invoice_number: str
    invoice_date: date
    document_type: Literal["INVOICE", "CREDIT_NOTE", "DEBIT_NOTE"]
    taxable_value: Decimal = Field(..., ge=0)
    igst_amount: Decimal = Field(..., ge=0)
    cgst_amount: Decimal = Field(..., ge=0)
    sgst_amount: Decimal = Field(..., ge=0)
    cess_amount: Decimal = Field(..., ge=0)
    total_invoice_value: Decimal = Field(..., ge=0)
    signed_qr_code: Optional[str] = None
    cancellation_date: Optional[date] = None
    cancellation_reason: Optional[str] = None
