"""Contract-4 response model: audit narrative derived from vendor risk."""

from pydantic import BaseModel, ConfigDict


class AuditNarrativeResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"entity": "AUDIT_NARRATIVE", "contract_version": "1.0.0"})

    contract_version: str = "1.0.0"
    entity: str = "AUDIT_NARRATIVE"
    gstin: str
    narrative: str
