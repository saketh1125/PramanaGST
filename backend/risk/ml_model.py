import os
import pickle
import numpy as np
import pandas as pd
from typing import Dict, Any, List
import logging
from sklearn.ensemble import RandomForestClassifier
import shap

logger = logging.getLogger(__name__)

# Selected numerical columns for training and predicting
FEATURE_COLUMNS = [
    "has_cancelled_registration",
    "total_invoices_issued",
    "total_taxable_value",
    "mismatch_rate",
    "missing_in_2b_rate",
    "payment_coverage",
    "filing_regularity",
    "late_filing_count",
    "circular_trade_involved"
]

MODEL_PATH = "backend/risk/model_artifact.pkl"
_model_cache = None

def _prepare_training_data(features_list: List[Dict[str, Any]]):
    """
    Creates synthetic pseudo-labels for training the Random Forest on our deterministic MVP data.
    """
    df = pd.DataFrame(features_list)
    
    # Fill missing columns with 0 if necessary
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0
            
    df["has_cancelled_registration"] = df["has_cancelled_registration"].astype(int)
    df["circular_trade_involved"] = df["circular_trade_involved"].astype(int)
    
    labels = []
    for _, row in df.iterrows():
        # High Risk Logic
        if row["has_cancelled_registration"] or \
           row["circular_trade_involved"] or \
           (row["mismatch_rate"] > 0.3 and row["payment_coverage"] < 0.5):
            labels.append("HIGH_RISK")
        # Medium Risk Logic
        elif row["mismatch_rate"] > 0.1 or row["payment_coverage"] < 0.8 or row["filing_regularity"] < 1.0:
            labels.append("MEDIUM_RISK")
        # Low Risk
        else:
            labels.append("LOW_RISK")
            
    df["risk_label"] = labels
    return df

def train_and_save_model(features_list: List[Dict[str, Any]]) -> bool:
    """Trains the Random Forest and saves it via pickle."""
    try:
        df = _prepare_training_data(features_list)
        if df.empty:
            return False
            
        X = df[FEATURE_COLUMNS]
        y = df["risk_label"]
        
        # We enforce class weight balanced to ensure we pay attention to small anomaly populations
        model = RandomForestClassifier(
            n_estimators=50, 
            max_depth=5, 
            random_state=42,
            class_weight="balanced"
        )
        model.fit(X, y)
        
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(model, f)
            
        global _model_cache
        _model_cache = model
        logger.info(f"Model trained and saved to {MODEL_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to train model: {e}")
        return False

def _load_model():
    global _model_cache
    if _model_cache is not None:
        return _model_cache
        
    try:
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, "rb") as f:
                _model_cache = pickle.load(f)
            return _model_cache
    except Exception as e:
        logger.error(f"Failed to load ML model: {e}")
        
    return None

def predict_risk(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predicts the risk label and returns the SHAP explanations for it.
    """
    model = _load_model()
    
    # Prepare the single row dataframe
    row = {col: features.get(col, 0) for col in FEATURE_COLUMNS}
    row["has_cancelled_registration"] = int(row["has_cancelled_registration"])
    row["circular_trade_involved"] = int(row["circular_trade_involved"])
    df_x = pd.DataFrame([row])
    
    if model is None:
        return {
            "predicted_label": "UNKNOWN",
            "confidence": 0.0,
            "probabilities": {"LOW_RISK": 0.0, "MEDIUM_RISK": 0.0, "HIGH_RISK": 0.0},
            "shap_explanation": None
        }

    try:
        pred_label = model.predict(df_x)[0]
        probas = model.predict_proba(df_x)[0]
        classes = model.classes_
        
        prob_dict = {cls: float(prob) for cls, prob in zip(classes, probas)}
        
        # Calculate SHAP explanation for the predicted class
        # Target index is the index of the predicted label
        target_idx = list(classes).index(pred_label)
        
        explainer = shap.TreeExplainer(model)
        # TreeExplainer for multiclass returns a list of shap arrays (one per class)
        shap_values_raw = explainer.shap_values(df_x)
        
        # Handle different SHAP versions / behaviors
        if isinstance(shap_values_raw, list):
            shap_vals_target = shap_values_raw[target_idx][0]
        else:
            # SHAP 0.40+ changed behavior to an array with 3 dimensions
            if len(shap_values_raw.shape) == 3:
                shap_vals_target = shap_values_raw[0, :, target_idx]
            else:
                 shap_vals_target = shap_values_raw[0]
                 
        feature_importance = {}
        top_factors = []
        
        for feature_name, shap_val in zip(FEATURE_COLUMNS, shap_vals_target):
            mag = abs(float(shap_val))
            direction = "increases risk" if shap_val > 0 else "decreases risk"
            
            # Contextualize: if model predicted LOW, a "positive" shap value pushes it towards LOW.
            # If model predicted HIGH, a positive shap pushes it towards HIGH.
            # We standardize language to "pushes towards [Label]" to avoid confusion.
            feature_importance[feature_name] = {
                "shap_value": float(shap_val),
                "direction": direction,
                "magnitude": mag
            }
            
            top_factors.append({
                "feature": feature_name,
                "direction": direction,
                "magnitude": mag
            })
            
        # Sort by impact sum magnitudes descending
        top_factors.sort(key=lambda x: x["magnitude"], reverse=True)
        
        return {
            "predicted_label": pred_label,
            "confidence": prob_dict.get(pred_label, 0.0),
            "probabilities": prob_dict,
            "shap_explanation": {
                "top_risk_factors": top_factors[:5], # Keep top 5
                "full_shap_values": feature_importance
            }
        }
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return {
            "predicted_label": "UNKNOWN",
            "confidence": 0.0,
            "probabilities": {},
            "shap_explanation": None
        }
