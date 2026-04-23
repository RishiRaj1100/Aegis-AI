"""
AegisAI - Catalyst Model Trainer
Trains an XGBoost model on historical task data to predict task success probabilities.
"""

import os
import pandas as pd
import xgboost as xgb
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score

def train_model(dataset_path="aegis_training_dataset.csv", output_dir="models/pretrained"):
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset not found at {dataset_path}")
        print("Please run generate_synthetic_dataset.py first.")
        return

    print("Loading dataset...")
    df = pd.read_csv(dataset_path)

    # Features and Labels
    X = df.drop(columns=["status"])
    y = df["status"]

    # Split dataset (80% training, 20% testing)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print(f"Training on {len(X_train)} samples, testing on {len(X_test)} samples.")

    # Initialize XGBoost Classifier
    print("Training XGBoost Catalyst Model...")
    model = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.1,
        objective="binary:logistic",
        eval_metric="logloss",
        use_label_encoder=False,
        random_state=42
    )

    # Train model
    model.fit(X_train, y_train)

    # Evaluate
    print("Evaluating Model...")
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)

    print(f"Accuracy: {accuracy:.2%}")
    print(f"ROC AUC Score: {auc:.4f}")
    print("\nClassification Report:\n", classification_report(y_test, y_pred))

    # Feature Importance
    importance = model.feature_importances_
    features = X.columns
    print("Top 3 Most Important Features:")
    for feature, score in sorted(zip(features, importance), key=lambda x: x[1], reverse=True)[:3]:
        print(f"  - {feature}: {score:.4f}")

    # Save model
    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, "catalyst_success_predictor.pkl")
    joblib.dump(model, model_path)
    
    print(f"\nModel successfully saved to {os.path.abspath(model_path)}")

if __name__ == "__main__":
    train_model()
