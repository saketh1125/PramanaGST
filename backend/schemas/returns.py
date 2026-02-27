from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date
from decimal import Decimal

class ReturnData(BaseModel):
    gstin: str = Field(..., pattern=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
    return_type: Literal["GSTR1", "GSTR2B", "GSTR3B"]
    return_period: str = Field(..., pattern=r'^(0[1-9]|1[0-2])\d{4}$')
    filing_date: Optional[date] = None
    filing_status: Literal["FILED", "NOT_FILED", "LATE_FILED"]
    arn: Optional[str] = None
    total_records: Optional[int] = Field(None, ge=0)
    aggregate_taxable_value: Optional[Decimal] = Field(None, ge=0)
    aggregate_igst: Optional[Decimal] = Field(None, ge=0)
    aggregate_cgst: Optional[Decimal] = Field(None, ge=0)
    aggregate_sgst: Optional[Decimal] = Field(None, ge=0)
    aggregate_cess: Optional[Decimal] = Field(None, ge=0)
