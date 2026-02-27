from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal

class MLExplanationFeature(BaseModel):
    feature: str
    direction: Literal["increases risk", "decreases risk"]
    magnitude: float

class MLExplanation(BaseModel):
    top_risk_factors: List[MLExplanationFeature]
    full_shap_values: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

class VendorRiskScore(BaseModel):
    gstin: str
    legal_name: str
    composite_score: float = Field(..., ge=0, le=100)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    rule_score: float = Field(..., ge=0, le=100)
    ml_score: float = Field(..., ge=0, le=100)
    graph_score: float = Field(..., ge=0, le=100)
    ml_prediction: str
    ml_confidence: float = Field(..., ge=0, le=1.0)
    triggered_rules: List[str]
    feature_values: Dict[str, Any]
    explanation: str
    ml_explanation: MLExplanation
