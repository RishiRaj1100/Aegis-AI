"""
AegisAI - Synthetic Dataset Generator
Generates a realistic CSV dataset of agent execution traces for training the Catalyst ML Model.
"""

import os
import numpy as np
import pandas as pd

def generate_dataset(num_samples=5000, output_path="aegis_training_dataset.csv"):
    np.random.seed(42)
    
    # ── Feature Generation ───────────────────────────────────────────────
    
    # Goal length (mostly short to medium, some long)
    goal_length_words = np.random.negative_binomial(15, 0.2, num_samples) + 5
    
    # Subtasks count (usually 3 to 8, correlated slightly with goal length)
    num_subtasks = np.clip(np.random.poisson(goal_length_words / 10) + 2, 1, 20)
    
    # Trust Components (0.0 to 1.0)
    clarity = np.clip(np.random.normal(0.7, 0.15, num_samples), 0.1, 1.0)
    info_quality = np.clip(np.random.normal(0.65, 0.2, num_samples), 0.1, 1.0)
    feasibility = np.clip(np.random.normal(0.6, 0.25, num_samples), 0.1, 1.0)
    manageability = np.clip(np.random.normal(0.75, 0.15, num_samples), 0.1, 1.0)
    resource_adequacy = np.clip(np.random.normal(0.5, 0.3, num_samples), 0.05, 1.0)
    uncertainty = np.clip(np.random.normal(0.3, 0.2, num_samples), 0.0, 1.0)
    
    # Context features
    past_success_rate = np.clip(np.random.normal(0.65, 0.1, num_samples), 0.2, 0.95)
    similarity_score = np.clip(np.random.beta(2, 5, num_samples), 0.0, 0.9)
    
    # ── Label Generation (Success vs Failure) ────────────────────────────
    
    # Calculate a "hidden" real probability based on the features to make the dataset realistic
    # Higher clarity, feasibility, resources, and past success increase success probability
    # Higher uncertainty decreases it
    hidden_score = (
        (clarity * 1.5) +
        (info_quality * 1.0) +
        (feasibility * 2.5) +
        (manageability * 1.0) +
        (resource_adequacy * 2.0) -
        (uncertainty * 1.5) +
        (past_success_rate * 1.5) +
        (similarity_score * 0.5) -
        (np.log1p(goal_length_words) * 0.2)
    )
    
    # Normalize and convert to probability using sigmoid
    def sigmoid(x):
        return 1 / (1 + np.exp(-x))
    
    # Shift and scale hidden_score so mean is around 0
    shifted_score = (hidden_score - np.mean(hidden_score)) / np.std(hidden_score) * 2.0 + 0.5
    probabilities = sigmoid(shifted_score)
    
    # Generate binary outcome (1 = COMPLETED, 0 = FAILED)
    status = np.random.binomial(1, probabilities)
    
    # ── Assemble DataFrame ───────────────────────────────────────────────
    df = pd.DataFrame({
        "goal_length_words": goal_length_words.astype(int),
        "num_subtasks": num_subtasks.astype(int),
        "clarity": np.round(clarity, 3),
        "info_quality": np.round(info_quality, 3),
        "feasibility": np.round(feasibility, 3),
        "manageability": np.round(manageability, 3),
        "resource_adequacy": np.round(resource_adequacy, 3),
        "uncertainty": np.round(uncertainty, 3),
        "past_success_rate": np.round(past_success_rate, 3),
        "similarity_score": np.round(similarity_score, 3),
        "status": status.astype(int)
    })
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Generated {num_samples} rows of synthetic training data.")
    print(f"Dataset saved to {os.path.abspath(output_path)}")
    print(f"Overall Success Rate: {df['status'].mean():.1%}")

if __name__ == "__main__":
    generate_dataset()
