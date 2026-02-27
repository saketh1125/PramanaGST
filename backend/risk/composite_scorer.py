import logging
from typing import Dict, Any, List

from .feature_engineer import compute_vendor_features
from .rule_scorer import compute_rule_score
from .ml_model import predict_risk, train_and_save_model
from .explainer import generate_explanation

from backend.schemas.risk import VendorRiskScore, MLExplanation, MLExplanationFeature

logger = logging.getLogger(__name__)

# Weights definition
WEIGHT_RULE = 0.40
WEIGHT_ML = 0.40
WEIGHT_GRAPH = 0.20


def compute_all_vendor_scores(
    gstins: List[str], 
    reconciliation_results: List[Any], 
    circular_trade_gstins: set
) -> List[VendorRiskScore]:
    """
    Computes the composite risk score for a list of vendors.
    """
    
    # 1. First, build all feature vectors
    all_features = []
    for gstin in gstins:
        features = compute_vendor_features(gstin, reconciliation_results, circular_trade_gstins)
        all_features.append(features)
        
    # 2. Train ML model on the batch if it's the first time
    # In a real app this is done asynchronously, but for MVP we train online
    logger.info("Training lightweight ML model on current extract...")
    train_and_save_model(all_features)
    
    # 3. Compute final scores
    scores = []
    for features in all_features:
        scores.append(compute_single_vendor(features))
        
    # Sort descending by risk score
    scores.sort(key=lambda x: x.composite_score, reverse=True)
    return scores


def compute_single_vendor(features: Dict[str, Any]) -> VendorRiskScore:
    """
    Runs the rules, the ML model, and graph centrality anomaly check,
    producing the weighted 0-100 VendorRiskScore.
    """
    
    gstin = features["gstin"]
    legal_name = features["legal_name"]
    
    # --- 1. Rule Score ---
    rule_score, triggered_rules = compute_rule_score(features)
    
    # --- 2. ML Score ---
    ml_result = predict_risk(features)
    
    # Convert ML prediction to a 0-100 score based on HIGH_RISK probability
    # If the model strongly predicts HIGH_RISK, the probability is near 1.0 (100)
    ml_prob_high = ml_result.get("probabilities", {}).get("HIGH_RISK", 0.0)
    ml_score = ml_prob_high * 100.0
    
    # Format the explanations to our schema
    shap_data = ml_result.get("shap_explanation")
    
    if shap_data:
        top_factors = [
            MLExplanationFeature(
                feature=f["feature"],
                direction=f["direction"],
                magnitude=f["magnitude"]
            )
            for f in shap_data.get("top_risk_factors", [])
        ]
        ml_explanation = MLExplanation(
            top_risk_factors=top_factors,
            full_shap_values=shap_data.get("full_shap_values", {})
        )
    else:
        ml_explanation = MLExplanation(top_risk_factors=[], full_shap_values={})
    
    # --- 3. Graph Score ---
    graph_score = _compute_graph_centrality_score(features)
    
    # --- 4. Composite Math ---
    composite_raw = (WEIGHT_RULE * rule_score) + (WEIGHT_ML * ml_score) + (WEIGHT_GRAPH * graph_score)
    composite_score = min(max(composite_raw, 0.0), 100.0)  # Bound 0-100
    
    # --- 5. Risk Tier ---
    risk_level = _assign_risk_tier(composite_score)
    
    # --- 6. Explanations ---
    explanation_text = generate_explanation(
        legal_name=legal_name,
        gstin=gstin,
        composite_score=composite_score,
        risk_level=risk_level,
        features=features,
        triggered_rules=triggered_rules
    )
    
    return VendorRiskScore(
        gstin=gstin,
        legal_name=legal_name,
        composite_score=round(composite_score, 1),
        risk_level=risk_level,
        rule_score=round(rule_score, 1),
        ml_score=round(ml_score, 1),
        graph_score=round(graph_score, 1),
        ml_prediction=ml_result.get("predicted_label", "UNKNOWN"),
        ml_confidence=round(ml_result.get("confidence", 0.0), 3),
        triggered_rules=triggered_rules,
        feature_values=features,
        explanation=explanation_text,
        ml_explanation=ml_explanation
    )


def _compute_graph_centrality_score(features: Dict[str, Any]) -> float:
    """
    Graph score calculation from §27. Based on node degree outliers and cycles.
    """
    degree = features.get("total_invoices_issued", 0)
    # Without full global context here, we use arbitrary static thresholds for MVP.
    # A true implementation queries Neo4j for avg_degree and std_degree across all tax_payers.
    
    AVG_DEGREE = 15  
    STD_DEGREE = 5
    
    outlier_score = 10.0 # normal baseline
    
    if degree > AVG_DEGREE + (2 * STD_DEGREE):
        outlier_score = 80.0 # unusually high
    elif degree < AVG_DEGREE - STD_DEGREE and degree > 0:
        outlier_score = 50.0 # unusually low but not zero
        
    # Crucial graph indicators
    if features.get("circular_trade_involved"):
        outlier_score += 30.0
        
    if features.get("has_cancelled_irn"):
        outlier_score += 20.0
        
    return min(outlier_score, 100.0)


def _assign_risk_tier(score: float) -> str:
    if score <= 30:
        return "LOW"
    elif score <= 60:
        return "MEDIUM"
    elif score <= 80:
        return "HIGH"
    else:
        return "CRITICAL"
