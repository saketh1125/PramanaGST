"""
INVOICE entity model — Contract v1.0.0.

Represents a GST invoice document linking a supplier to a recipient,
with itemized tax components (IGST, CGST, SGST, Cess).
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .enums import DocumentType, InvoiceStatus, InvoiceType, SupplyType


class Invoice(BaseModel):
    """
    Canonical schema for the INVOICE entity.

    Monetary fields use Decimal for financial precision.
    The filing_period is encoded as MMYYYY (e.g., "012026" for Jan 2026).
    """

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "entity": "INVOICE",
            "contract_version": "1.0.0",
        },
    )

    invoice_number: str = Field(
        ...,
        alias="invoiceNumber",
        min_length=1,
        max_length=50,
        description="Unique invoice number",
    )

    invoice_date: date = Field(
        ...,
        alias="invoiceDate",
        description="Date of invoice issuance",
    )

    invoice_type: InvoiceType = Field(
        ...,
        alias="invoiceType",
        description="Classification of the invoice (B2B, B2C, etc.)",
    )

    invoice_status: InvoiceStatus = Field(
        ...,
        alias="invoiceStatus",
        description="Current status of the invoice",
    )

    supply_type: SupplyType = Field(
        ...,
        alias="supplyType",
        description="Whether the supply is intra-state or inter-state",
    )

    document_type: DocumentType = Field(
        ...,
        alias="documentType",
        description="Document type — INV, CRN, or DBN",
    )

    supplier_gstin: str = Field(
        ...,
        alias="supplierGstin",
        min_length=15,
        max_length=15,
        pattern=r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$",
        description="GSTIN of the supplier",
    )

    recipient_gstin: Optional[str] = Field(
        None,
        alias="recipientGstin",
        min_length=15,
        max_length=15,
        pattern=r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$",
        description="GSTIN of the recipient (None for B2C transactions)",
    )

    taxable_value: Decimal = Field(
        ...,
        alias="taxableValue",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Pre-tax invoice amount",
    )

    igst_amount: Decimal = Field(
        ...,
        alias="igstAmount",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="IGST component",
    )

    cgst_amount: Decimal = Field(
        ...,
        alias="cgstAmount",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="CGST component",
    )

    sgst_amount: Decimal = Field(
        ...,
        alias="sgstAmount",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="SGST component",
    )

    cess_amount: Decimal = Field(
        ...,
        alias="cessAmount",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Cess component",
    )

    total_value: Decimal = Field(
        ...,
        alias="totalValue",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Total invoice value (taxable + all taxes)",
    )

    place_of_supply: str = Field(
        ...,
        alias="placeOfSupply",
        min_length=2,
        max_length=2,
        pattern=r"^[0-9]{2}$",
        description="Two-digit state code for place of supply",
        examples=["27"],
    )

    reverse_charge: bool = Field(
        ...,
        alias="reverseCharge",
        description="Whether reverse charge mechanism is applicable",
    )

    irn: Optional[str] = Field(
        None,
        alias="irn",
        max_length=64,
        description="Linked Invoice Reference Number, if e-invoiced",
    )

    filing_period: str = Field(
        ...,
        alias="filingPeriod",
        min_length=6,
        max_length=6,
        pattern=r"^(0[1-9]|1[0-2])\d{4}$",
        description="Filing period in MMYYYY format",
        examples=["012026"],
    )
