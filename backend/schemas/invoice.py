from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Optional, List
from datetime import date, timedelta
from decimal import Decimal

class HSNItem(BaseModel):
    hsn_code: str = Field(..., min_length=4, max_length=8)
    description: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    taxable_value: Decimal = Field(..., ge=0)
    tax_rate: Decimal = Field(..., ge=0)
    igst_amount: Decimal = Field(..., ge=0)
    cgst_amount: Decimal = Field(..., ge=0)
    sgst_amount: Decimal = Field(..., ge=0)
    cess_amount: Decimal = Field(..., ge=0)

class InvoiceData(BaseModel):
    invoice_number: str = Field(..., min_length=1)
    original_invoice_number: str
    invoice_date: date
    financial_year: str = Field(..., pattern=r'^\d{4}-\d{2}$')
    invoice_type: Literal["B2B", "B2C_LARGE", "B2C_SMALL", "EXPORT", "CDNR", "CDNUR", "SEZ", "DEEMED_EXPORT", "NIL_RATED", "ADVANCE_RECEIVED", "ADVANCE_ADJUSTED"]
    document_type: Literal["INVOICE", "CREDIT_NOTE", "DEBIT_NOTE"]
    supplier_gstin: str = Field(..., pattern=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
    recipient_gstin: Optional[str] = Field(None, pattern=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
    place_of_supply: str = Field(..., pattern=r'^[0-9]{2}$')
    supply_type: Literal["INTER_STATE", "INTRA_STATE"]
    reverse_charge: bool
    taxable_value: Decimal = Field(..., ge=0)
    igst_amount: Decimal = Field(..., ge=0)
    cgst_amount: Decimal = Field(..., ge=0)
    sgst_amount: Decimal = Field(..., ge=0)
    cess_amount: Decimal = Field(default=Decimal("0.0"), ge=0)
    total_tax_amount: Decimal = Field(..., ge=0)
    total_invoice_value: Decimal = Field(..., ge=0)
    irn: Optional[str] = None
    linked_irn_entity_ref_id: Optional[str] = None
    original_invoice_ref: Optional[str] = None
    original_invoice_date: Optional[date] = None
    hsn_items: Optional[List[HSNItem]] = None

    @field_validator('invoice_date')
    @classmethod
    def validate_invoice_date(cls, v: date) -> date:
        if v > date.today() + timedelta(days=1):
            raise ValueError("Invoice date cannot be in the future beyond 1 day")
        return v

    @model_validator(mode='after')
    def validate_totals_and_taxes(self) -> 'InvoiceData':
        TOLERANCE = Decimal("1.00")
        
        calculated_tax = self.igst_amount + self.cgst_amount + self.sgst_amount + self.cess_amount
        if abs(calculated_tax - self.total_tax_amount) > TOLERANCE:
            raise ValueError("Total tax amount does not equal sum of IGST, CGST, SGST, and CESS")
            
        calculated_total = self.taxable_value + self.total_tax_amount
        if abs(calculated_total - self.total_invoice_value) > TOLERANCE:
            raise ValueError("Total invoice value does not equal taxable value plus total tax amount")
            
        if self.supply_type == "INTER_STATE":
            if self.cgst_amount != Decimal("0.0") or self.sgst_amount != Decimal("0.0"):
                raise ValueError("CGST and SGST must be 0 for INTER_STATE supply")
        elif self.supply_type == "INTRA_STATE":
            if self.igst_amount != Decimal("0.0"):
                raise ValueError("IGST must be 0 for INTRA_STATE supply")
                
        if self.invoice_type == "B2B" and not self.recipient_gstin:
            raise ValueError("recipient_gstin is required for B2B invoice_type")
            
        return self
