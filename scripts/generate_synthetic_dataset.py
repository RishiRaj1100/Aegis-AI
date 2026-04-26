"""
AegisAI - Synthetic Dataset Generator
Generates a realistic CSV dataset of agent execution traces for training the ML Models.
"""

import numpy as np
import pandas as pd

def generate_dataset(num_samples=5000, output_path="aegis_training_dataset.csv"):
    np.random.seed(42)
    
    # ── Feature Generation ───────────────────────────────────────────────
    
    # Basic Features
    task_length = np.random.negative_binomial(15, 0.2, num_samples) + 5
    deadline_days = np.random.randint(1, 31, num_samples)
    complexity = np.clip(np.random.normal(0.5, 0.2, num_samples), 0.1, 1.0)
    resources = np.clip(np.random.normal(0.6, 0.25, num_samples), 0.1, 1.0)
    dependencies = np.random.poisson(2, num_samples)
    priority = np.random.randint(1, 6, num_samples)
    
    # Derived Features (as requested)
    deadline_urgency = priority / deadline_days
    resource_efficiency = resources / (complexity + 0.1)  # avoid div zero
    
    # ── Label Generation (Success vs Failure) ────────────────────────────
    
    def sigmoid(x):
        return 1 / (1 + np.exp(-x))

    # Hidden score for success
    hidden_success_score = (
        (resources * 2.5) -
        (complexity * 1.5) -
        (dependencies * 0.5) +
        (deadline_days * 0.1) +
        (priority * 0.2) +
        (resource_efficiency * 1.0) -
        (deadline_urgency * 0.5) -
        (np.log1p(task_length) * 0.2)
    )
    
    success_prob = sigmoid((hidden_success_score - np.mean(hidden_success_score)) / np.std(hidden_success_score) * 2.0)
    success = np.random.binomial(1, success_prob)

    # ── Label Generation (Delay vs On-time) ─────────────────────────────
    
    hidden_delay_score = (
        (complexity * 2.0) +
        (dependencies * 1.5) +
        (deadline_urgency * 1.0) -
        (resources * 1.5) -
        (deadline_days * 0.1) +
        (np.random.normal(0, 0.5, num_samples))
    )
    
    delay_prob = sigmoid((hidden_delay_score - np.mean(hidden_delay_score)) / np.std(hidden_delay_score) * 2.0)
    delay = np.random.binomial(1, delay_prob)
    
    # ── Assemble DataFrame ───────────────────────────────────────────────
    df = pd.DataFrame({
        "task_id": [f"TASK-{i}" for i in range(num_samples)],
        "task": [f"Simulated task {i} with {length} words" for i, length in enumerate(task_length)],
        "task_length": task_length.astype(int),
        "deadline_days": deadline_days.astype(int),
        "complexity": np.round(complexity, 3),
        "resources": np.round(resources, 3),
        "dependencies": dependencies.astype(int),
        "priority": priority.astype(int),
        "deadline_urgency": np.round(deadline_urgency, 3),
        "resource_efficiency": np.round(resource_efficiency, 3),
        "success": success.astype(int),
        "delay": delay.astype(int)
    })
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Generated {num_samples} rows of training data.")
    print(f"Overall Success Rate: {df['success'].mean():.1%}")
    print(f"Overall Delay Rate: {df['delay'].mean():.1%}")

if __name__ == "__main__":
    generate_dataset()
