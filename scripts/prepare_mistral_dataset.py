"""
AegisAI - Mistral Dataset Preparation
Converts the locked numerical schema (aegis_training_dataset.csv) into 
a conversational JSONL format designed for Mistral-7B-Instruct fine-tuning.
"""

import pandas as pd
import json
import os

def prepare_dataset(input_csv="data/processed/final_dataset.csv", output_jsonl="mistral_training_data.jsonl"):
    # Fallback to the root dataset if merged one isn't ready
    if not os.path.exists(input_csv):
        input_csv = "aegis_training_dataset.csv"
        
    if not os.path.exists(input_csv):
        print(f"Error: Could not find {input_csv}. Run generate_synthetic_dataset.py or merge_datasets.py first.")
        return

    print(f"Loading {input_csv}...")
    df = pd.read_csv(input_csv)
    
    jsonl_data = []
    
    for _, row in df.iterrows():
        is_real = str(row.get("task_id", "")).startswith("REAL")
        
        # Build the prompt
        instruction = (
            "Analyze the following task parameters and determine the execution risk. "
            "Predict if the task will succeed or fail, and if it will face delays. Provide reasoning based on the parameters.\n\n"
            f"Task Description: {row.get('task', 'N/A')}\n"
            f"Deadline Days: {row.get('deadline_days', 0)}\n"
            f"Complexity Score: {row.get('complexity', 0):.2f}\n"
            f"Resources Score: {row.get('resources', 0):.2f}\n"
            f"Dependencies: {row.get('dependencies', 0)}\n"
            f"Priority: {row.get('priority', 3)}\n"
        )
        
        # Determine the textual outcome based on binary labels
        success_status = "succeed" if row.get("success", 0) == 1 else "fail"
        delay_status = "be delayed" if row.get("delay", 0) == 1 else "complete on time"
        
        # Generate reasoning logic
        reasoning_points = []
        if is_real:
            # More sophisticated reasoning for real tasks
            if row.get("success", 0) == 1:
                reasoning_points.append(f"Despite its complexity ({row.get('complexity'):.2f}), the '{row.get('task')}' is mission-ready due to strong resource allocation.")
            else:
                reasoning_points.append(f"The '{row.get('task')}' faces significant risk. With {row.get('dependencies')} dependencies and limited resources, success is unlikely within {row.get('deadline_days')} days.")
            
            if row.get("delay", 0) == 1:
                reasoning_points.append("Strategic bottlenecks and dependency chains suggest a high probability of timeline slippage.")
        else:
            # Basic reasoning for simulated tasks
            if row.get("complexity", 0) > 0.7:
                reasoning_points.append("The task has high complexity.")
            if row.get("resources", 0) < 0.4:
                reasoning_points.append("There is a severe lack of resources.")
            if row.get("dependencies", 0) > 3:
                reasoning_points.append("There are too many external dependencies.")
            if row.get("deadline_days", 30) < 7:
                reasoning_points.append("The deadline is extremely tight.")
            if not reasoning_points:
                reasoning_points.append("The task parameters are well-balanced and within safe thresholds.")
            
        reasoning_text = " ".join(reasoning_points)
        
        output = (
            f"Based on the provided parameters, this task is highly likely to {success_status} "
            f"and will probably {delay_status}. {reasoning_text}"
        )
        
        # Mistral-Instruct V0.2 exact formatting
        # <s>[INST] Instruction [/INST] Output</s>
        text = f"<s>[INST] {instruction} [/INST] {output}</s>"
        
        jsonl_data.append({"text": text})

    # Save to JSONL
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for item in jsonl_data:
            f.write(json.dumps(item) + "\n")
            
    print(f"Successfully generated {len(jsonl_data)} conversational training samples.")
    print(f"Saved to {os.path.abspath(output_jsonl)}")
    print("You can now upload this file to Google Colab for fine-tuning!")

if __name__ == "__main__":
    prepare_dataset()
