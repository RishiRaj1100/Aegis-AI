import joblib
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

success_path = os.path.join("models", "pretrained", "catalyst_success_predictor.pkl")
delay_path = os.path.join("models", "pretrained", "behavior_model.pkl")

if os.path.exists(success_path):
    print(f"Loading success model from {success_path}...")
    model = joblib.load(success_path)
    print("Success model loaded.")

if os.path.exists(delay_path):
    print(f"Loading delay model from {delay_path}...")
    model = joblib.load(delay_path)
    print("Delay model loaded.")
