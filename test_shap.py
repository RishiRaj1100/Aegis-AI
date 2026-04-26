import os
import sys
import pandas as pd
import joblib

# Add project root to sys.path
sys.path.append(os.getcwd())

from services.explainability import get_explainability_service

def test_shap():
    print("Testing SHAP Explainability Service...")
    explainer = get_explainability_service()
    
    # Load the model
    model_path = "models/pretrained/catalyst_success_predictor.pkl"
    if not os.path.exists(model_path):
        print(f"Model not found: {model_path}")
        return
        
    model = joblib.load(model_path)
    
    # Mock features
    features = pd.DataFrame([{
        "deadline_days": 15.0,
        "complexity": 0.5,
        "resources": 1.0,
        "dependencies": 2.0,
        "priority": 3.0,
        "task_length": 50.0,
        "deadline_urgency": 0.2,
        "resource_efficiency": 2.0,
    }])
    
    try:
        shap_map, pos, neg = explainer.explain_prediction(model=model, features=features)
        print("\nSHAP Map:")
        for k, v in shap_map.items():
            print(f"  {k}: {v:.4f}")
        print("\nPositive Factors:", pos)
        print("\nNegative Factors:", neg)
        print("\nTest passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_shap()
