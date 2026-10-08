"""Contract-5 view models: API -> Frontend Dashboard.

These are UI-oriented projections. Contract 4 (VendorRisk) remains the
authoritative risk payload; VendorRiskView/RiskSummary are derived from
the same data for dashboard consumption. No Risk AI semantics live here.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

_CONTRACT = {"contract_version": "1.0.0"}


class RiskSummary(BaseModel):
    model_config = ConfigDict(json_schema_extra={"entity": "RISK_SUMMARY"})

    contract_version: str = "1.0.0"
    entity: str = "RISK_SUMMARY"
    totalVendors: int = Field(..., ge=0)
    highRisk: int = Field(..., ge=0)
    mediumRisk: int = Field(..., ge=0)
    lowRisk: int = Field(..., ge=0)
    averageScore: float = Field(..., ge=0, le=100)


class VendorRiskView(BaseModel):
    """Flattened presentation projection of Contract 4 VendorRisk.

    Detailed risk signals (mismatchedClaims, unreportedInvoices,
    taxLiability, taxPaid, shortfall, inCycle) are intentionally omitted;
    fetch them from GET /api/v1/risks/{gstin}.
    """

    model_config = ConfigDict(json_schema_extra={"entity": "VENDOR_RISK_VIEW"})

    contract_version: str = "1.0.0"
    entity: str = "VENDOR_RISK_VIEW"
    gstin: str
    legal_name: str = Field(..., alias="legalName")
    score: float = Field(..., ge=0, le=100)
    band: str
    reasons: list[str] = Field(default_factory=list)
    invoicesIssued: int = Field(..., ge=0)


class GraphNode(BaseModel):
    """Whitelisted node payload for the dashboard force graph.

    No contract_version/entity per node: the GraphView envelope carries
    the metadata. extra="forbid" keeps internal graph attributes out.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    label: str
    legal_name: Optional[str] = Field(default=None, alias="legalName")
    invoice_number: Optional[str] = Field(default=None, alias="invoiceNumber")
    return_id: Optional[str] = Field(default=None, alias="returnId")


class GraphLink(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    source: str
    target: str
    type: Optional[str] = None


class GraphView(BaseModel):
    model_config = ConfigDict(json_schema_extra={"entity": "GRAPH_VIEW"})

    contract_version: str = "1.0.0"
    entity: str = "GRAPH_VIEW"
    nodes: list[GraphNode] = Field(default_factory=list)
    links: list[GraphLink] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"entity": "ERROR"})

    contract_version: str = "1.0.0"
    entity: str = "ERROR"
    error: ErrorDetail
