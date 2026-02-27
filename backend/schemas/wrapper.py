from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any
from datetime import datetime

class SourceContext(BaseModel):
    source_system: Literal["GSTR1", "GSTR2B", "PURCHASE_REGISTER", "E_INVOICE", "TAX_PAYMENT"]
    source_section: Optional[str] = None
    reporter_gstin: str
    reporter_role: Literal["SUPPLIER", "BUYER", "SYSTEM", "PAYER"]
    reporting_period: str
    original_record_index: int
    source_file: str

class ValidationWarning(BaseModel):
    field: str
    code: str
    message: str

class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[ValidationWarning] = Field(default_factory=list)
    warnings: List[ValidationWarning] = Field(default_factory=list)

class Lineage(BaseModel):
    batch_id: str
    ingestion_timestamp: datetime
    record_hash: str
    schema_version: str = "1.0.0"
    transformations_applied: List[str] = Field(default_factory=list)

class GraphHints(BaseModel):
    expected_node_label: str
    foreign_keys: Dict[str, Optional[str]] = Field(default_factory=dict)

class RecordWrapper(BaseModel):
    entity_type: Literal["TAXPAYER", "INVOICE", "RETURN", "PAYMENT", "IRN"]
    entity_ref_id: str
    source_record_id: str
    data: Dict[str, Any]
    source_context: SourceContext
    lineage: Lineage
    validation_result: ValidationResult
    graph_hints: GraphHints

class BatchMetadata(BaseModel):
    batch_id: str
    source_system: str
    timestamp: datetime
    record_count: int

class EntityCollection(BaseModel):
    taxpayers: List[RecordWrapper] = Field(default_factory=list)
    invoices: List[RecordWrapper] = Field(default_factory=list)
    returns: List[RecordWrapper] = Field(default_factory=list)
    payments: List[RecordWrapper] = Field(default_factory=list)
    irns: List[RecordWrapper] = Field(default_factory=list)

class BatchEnvelope(BaseModel):
    contract_version: str = "1.0.0"
    batch_metadata: BatchMetadata
    entities: EntityCollection
    rejected_records: List[Dict[str, Any]] = Field(default_factory=list)
