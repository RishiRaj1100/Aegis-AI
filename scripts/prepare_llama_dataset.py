"""
AegisAI - Llama 3.2 Dataset Preparation
Converts the numerical schema (aegis_training_dataset.csv) into 
a conversational JSONL format designed for Llama-3.2-1B-Instruct fine-tuning.
"""

import pandas as pd
import json
import os

def prepare_dataset(input_csv="data/processed/final_dataset.csv", output_jsonl="llama_training_data.jsonl"):
    if not os.path.exists(input_csv):
        # Fallback to root dataset if merged one is missing
        alternate_path = "aegis_training_dataset.csv"
        if os.path.exists(alternate_path):
            input_csv = alternate_path
        else:
            print(f"Error: Could not find dataset {input_csv}. Run generate_synthetic_dataset.py first.")
            return

    print(f"Loading {input_csv}...")
    df = pd.read_csv(input_csv)
    
    jsonl_data = []
    
    # System prompt for Aegis Brain
    system_prompt = (
        "You are Aegis Brain, a specialized task analysis and risk prediction AI. "
        "Your goal is to analyze task parameters and predict execution success and delays with detailed reasoning."
    )
    
    for _, row in df.iterrows():
        # User input (Task parameters)
        # Using .get() with defaults to handle potential missing columns
        task_name = row.get("task", "Unnamed Task")
        deadline = row.get("deadline_days", 0)
        complexity = row.get("complexity", 0.5)
        resources = row.get("resources", 0.5)
        dependencies = row.get("dependencies", 0)
        priority = row.get("priority", 3)

        user_input = (
            "Analyze the following task parameters:\n"
            f"- Task: {task_name}\n"
            f"- Deadline: {deadline} days\n"
            f"- Complexity: {complexity:.2f}/1.0\n"
            f"- Resources: {resources:.2f}/1.0\n"
            f"- Dependencies: {dependencies}\n"
            f"- Priority: {priority}"
        )
        
        # Determine the textual outcome
        success_val = row.get("success", 0)
        delay_val = row.get("delay", 0)
        
        success_status = "SUCCEED" if success_val == 1 else "FAIL"
        delay_status = "DELAYED" if delay_val == 1 else "ON TIME"
        
        # Generate reasoning logic based on the actual outcome and parameters
        reasoning_points = []
        if success_val == 1:
            if resources > 0.7:
                reasoning_points.append(f"High resource availability ({resources:.2f}) mitigates complexity risks.")
            if complexity < 0.4:
                reasoning_points.append("Low complexity allows for straightforward execution.")
        else:
            if complexity > 0.7:
                reasoning_points.append(f"High complexity ({complexity:.2f}) exceeds current capacity.")
            if resources < 0.4:
                reasoning_points.append("Critical resource shortage detected.")
            if dependencies > 3:
                reasoning_points.append(f"High dependency count ({dependencies}) creates bottleneck risks.")

        if not reasoning_points:
            reasoning_points.append("Standard operational parameters with balanced risk factors.")
            
        reasoning_text = " ".join(reasoning_points)
        
        # Assistant output
        assistant_output = (
            f"PREDICTION: {success_status}\n"
            f"TIMELINE: {delay_status}\n"
            f"REASONING: {reasoning_text}"
        )
        
        # Llama 3.2 Instruct format
        # Reference: https://www.llama.com/docs/model-cards-and-prompt-formats/llama-3-1/
        text = (
            f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|>"
            f"<|start_header_id|>user<|end_header_id|>\n\n{user_input}<|eot_id|>"
            f"<|start_header_id|>assistant<|end_header_id|>\n\n{assistant_output}<|eot_id|>"
        )
        
        jsonl_data.append({"text": text})

    # Save to JSONL
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for item in jsonl_data:
            f.write(json.dumps(item) + "\n")
            
    print(f"Successfully generated {len(jsonl_data)} samples for Llama 3.2.")
    print(f"Saved to {os.path.abspath(output_jsonl)}")

if __name__ == "__main__":
    prepare_dataset()
