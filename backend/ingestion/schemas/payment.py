"""
PAYMENT entity model — Contract v1.0.0.

Represents a GST payment made against a return period,
broken down by tax component and payment mode.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .enums import PaymentMode, PaymentStatus


class Payment(BaseModel):
    """
    Canonical schema for the PAYMENT entity.

    Each payment is linked to a GSTIN and a return period.
    Payment may be through cash ledger or ITC utilization.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "entity": "PAYMENT",
            "contract_version": "1.0.0",
        },
    )

    payment_id: str = Field(
        ...,
        alias="paymentId",
        min_length=1,
        max_length=100,
        description="Unique payment identifier",
    )

    gstin: str = Field(
        ...,
        alias="gstin",
        min_length=15,
        max_length=15,
        pattern=r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$",
        description="GSTIN of the payer",
    )

    return_period: str = Field(
        ...,
        alias="returnPeriod",
        min_length=6,
        max_length=6,
        pattern=r"^(0[1-9]|1[0-2])\d{4}$",
        description="Return period for which payment is made (MMYYYY)",
        examples=["012026"],
    )

    payment_date: date = Field(
        ...,
        alias="paymentDate",
        description="Date of payment",
    )

    payment_mode: PaymentMode = Field(
        ...,
        alias="paymentMode",
        description="Mode of payment (CASH, ITC_IGST, etc.)",
    )

    payment_status: PaymentStatus = Field(
        ...,
        alias="paymentStatus",
        description="Current payment status",
    )

    igst_paid: Decimal = Field(
        ...,
        alias="igstPaid",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="IGST component paid",
    )

    cgst_paid: Decimal = Field(
        ...,
        alias="cgstPaid",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="CGST component paid",
    )

    sgst_paid: Decimal = Field(
        ...,
        alias="sgstPaid",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="SGST component paid",
    )

    cess_paid: Decimal = Field(
        ...,
        alias="cessPaid",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Cess component paid",
    )

    total_paid: Decimal = Field(
        ...,
        alias="totalPaid",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Total payment amount",
    )

    challan_number: Optional[str] = Field(
        None,
        alias="challanNumber",
        max_length=50,
        description="CIN / Challan identification number",
    )

    bank_reference: Optional[str] = Field(
        None,
        alias="bankReference",
        max_length=50,
        description="Bank reference number (BRN)",
    )
