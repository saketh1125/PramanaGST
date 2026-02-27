from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date

class TaxpayerData(BaseModel):
    gstin: str = Field(..., min_length=15, max_length=15, pattern=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
    legal_name: str = Field(..., min_length=1, max_length=256)
    trade_name: Optional[str] = Field(None, max_length=256)
    state_code: str = Field(..., min_length=2, max_length=2, pattern=r'^[0-9]{2}$')
    registration_type: Literal["REGULAR", "COMPOSITION", "ISD", "TDS", "TCS", "NRTP", "CASUAL", "SEZ_UNIT", "SEZ_DEVELOPER"]
    status: Literal["ACTIVE", "CANCELLED", "SUSPENDED"]
    registration_date: Optional[date] = None
    cancellation_date: Optional[date] = None
    pan: Optional[str] = Field(None, pattern=r'^[A-Z]{5}[0-9]{4}[A-Z]$')
