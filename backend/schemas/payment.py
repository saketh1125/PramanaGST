from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date
from decimal import Decimal

class PaymentData(BaseModel):
    gstin: str = Field(..., pattern=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
    challan_number: str = Field(..., min_length=1)
    payment_date: date
    tax_period: str = Field(..., pattern=r'^(0[1-9]|1[0-2])\d{4}$')
    payment_mode: Literal["CASH", "NEFT", "OTC", "ITC_UTILIZATION"]
    igst_paid: Decimal = Field(..., ge=0)
    cgst_paid: Decimal = Field(..., ge=0)
    sgst_paid: Decimal = Field(..., ge=0)
    cess_paid: Decimal = Field(..., ge=0)
    interest_paid: Decimal = Field(..., ge=0)
    penalty_paid: Decimal = Field(..., ge=0)
    total_paid: Decimal = Field(..., ge=0)
    payment_status: Literal["SUCCESS", "FAILED", "PENDING"]
    bank_reference: Optional[str] = None
