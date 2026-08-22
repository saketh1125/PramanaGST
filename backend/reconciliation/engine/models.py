"""
Reconciliation evidence models — GRAPH ↔ RECONCILIATION interface (Contract 2).

Every finding carries its graph path as proof ("pramana").
"""

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReconStatus(str, Enum):
    MATCHED = "MATCHED"
    MISMATCHED = "MISMATCHED"
    UNREPORTED = "UNREPORTED"  # claim exists but supplier never reported the invoice


class ReconItem(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={"entity": "RECON_ITEM", "contract_version": "1.0.0"},
    )

    claim_ref: str = Field(..., alias="claimRef", description="Claim observation reference")
    status: ReconStatus = Field(..., description="Reconciliation outcome")
    invoice_number: str = Field(..., alias="invoiceNumber")
    supplier_gstin: str = Field(..., alias="supplierGstin")
    recipient_gstin: str = Field(..., alias="recipientGstin")
    period: str = Field(..., description="MMYYYY claim period")

    itc_claimed: Decimal = Field(..., alias="itcClaimed", ge=0)
    invoice_tax_total: Decimal = Field(..., alias="invoiceTaxTotal", ge=0)

    variance: Decimal = Field(
        ...,
        description="invoice_tax_total - itc_claimed; 0 for matched/unreported",
    )

    evidence_path: list[str] = Field(..., alias="evidencePath",
                                     description="Ordered node keys proving this outcome")


class ReconSummary(BaseModel):
    model_config = ConfigDict(json_schema_extra={"entity": "RECON_SUMMARY", "contract_version": "1.0.0"})

    total_claims: int = Field(..., alias="totalClaims", ge=0)
    matched: int = Field(..., ge=0)
    mismatched: int = Field(..., ge=0)
    unreported: int = Field(..., ge=0)

    claimed_total: Decimal = Field(..., alias="claimedTotal", ge=0,
                                   description="Total ITC claimed across all claims")
    variance_total: Decimal = Field(..., alias="varianceTotal",
                                    description="Net tax-at-risk across all findings")
    match_rate: float = Field(..., alias="matchRate", ge=0, le=100)


class ReconReport(BaseModel):
    model_config = ConfigDict(json_schema_extra={"entity": "RECON_REPORT", "contract_version": "1.0.0"})

    summary: ReconSummary
    items: list[ReconItem]
