"""
RETURN (ReturnFiling) entity model — Contract v1.0.0.

Represents a GST return filed by a taxpayer for a given period,
including tax liabilities and ITC claims across all components.

Named ReturnFiling to avoid collision with Python's `return` keyword.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .enums import GSTReturnType, ReturnFilingStatus


class ReturnFiling(BaseModel):
    """
    Canonical schema for the RETURN entity.

    Captures both the tax liability side (total_igst, total_cgst, etc.)
    and the ITC claim side (itc_claimed_igst, itc_claimed_cgst, etc.)
    for a single return filing period.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "entity": "RETURN",
            "contract_version": "1.0.0",
        },
    )

    return_id: str = Field(
        ...,
        alias="returnId",
        min_length=1,
        max_length=100,
        description="Unique return identifier",
    )

    gstin: str = Field(
        ...,
        alias="gstin",
        min_length=15,
        max_length=15,
        pattern=r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$",
        description="GSTIN of the filer",
    )

    return_type: GSTReturnType = Field(
        ...,
        alias="returnType",
        description="Type of return (GSTR1, GSTR3B, etc.)",
    )

    return_period: str = Field(
        ...,
        alias="returnPeriod",
        min_length=6,
        max_length=6,
        pattern=r"^(0[1-9]|1[0-2])\d{4}$",
        description="Filing period in MMYYYY format",
        examples=["012026"],
    )

    filing_date: Optional[date] = Field(
        None,
        alias="filingDate",
        description="Date on which the return was filed",
    )

    filing_status: ReturnFilingStatus = Field(
        ...,
        alias="filingStatus",
        description="Current filing status",
    )

    # --- Tax Liability ---

    total_taxable_value: Decimal = Field(
        ...,
        alias="totalTaxableValue",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Total taxable turnover for the period",
    )

    total_igst: Decimal = Field(
        ...,
        alias="totalIgst",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Total IGST liability",
    )

    total_cgst: Decimal = Field(
        ...,
        alias="totalCgst",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Total CGST liability",
    )

    total_sgst: Decimal = Field(
        ...,
        alias="totalSgst",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Total SGST liability",
    )

    total_cess: Decimal = Field(
        ...,
        alias="totalCess",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Total cess liability",
    )

    total_tax_liability: Decimal = Field(
        ...,
        alias="totalTaxLiability",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Sum of all tax components",
    )

    # --- ITC Claims ---

    itc_claimed_igst: Decimal = Field(
        ...,
        alias="itcClaimedIgst",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Input Tax Credit claimed — IGST",
    )

    itc_claimed_cgst: Decimal = Field(
        ...,
        alias="itcClaimedCgst",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Input Tax Credit claimed — CGST",
    )

    itc_claimed_sgst: Decimal = Field(
        ...,
        alias="itcClaimedSgst",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Input Tax Credit claimed — SGST",
    )

    itc_claimed_cess: Decimal = Field(
        ...,
        alias="itcClaimedCess",
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Input Tax Credit claimed — Cess",
    )
