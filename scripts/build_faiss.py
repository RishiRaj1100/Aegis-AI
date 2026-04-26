import os
import joblib
import faiss
import numpy as np
import pandas as pd
from datetime import datetime
from sentence_transformers import SentenceTransformer

def build_faiss():
    print("Initializing FAISS Retrieval System with rich metadata...")
    
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    model = SentenceTransformer(model_name)
    dimension = 384
    
    # Initialize index
    index = faiss.IndexFlatIP(dimension)
    
    # Load data
    dataset_path = "aegis_training_dataset.csv"
    if not os.path.exists(dataset_path):
        print(f"Error: {dataset_path} not found. Run generate_synthetic_dataset.py first.")
        return
        
    df = pd.read_csv(dataset_path)
    
    # Create metadata records
    metadata = []
    texts = []
    
    for _, row in df.iterrows():
        # Text representation for embedding
        text_rep = f"{row['task']} (Priority: {row['priority']}, Complexity: {row['complexity']})"
        texts.append(text_rep)
        
        # Rich metadata
        metadata.append({
            "task_id": row["task_id"],
            "task": row["task"],
            "task_length": row["task_length"],
            "deadline_days": row["deadline_days"],
            "complexity": row["complexity"],
            "resources": row["resources"],
            "dependencies": row["dependencies"],
            "priority": row["priority"],
            "success": bool(row["success"]),
            "delay": bool(row["delay"]),
            "timestamp": datetime.now().isoformat()
        })
    
    print(f"Encoding {len(texts)} tasks...")
    # Batch encoding to prevent memory issues
    embeddings = model.encode(texts, batch_size=256, show_progress_bar=True, normalize_embeddings=True)
    
    index.add(np.asarray(embeddings, dtype=np.float32))
    
    # Save index and metadata
    model_dir = "models/pretrained"
    os.makedirs(model_dir, exist_ok=True)
    
    faiss.write_index(index, os.path.join(model_dir, "tasks.faiss"))
    joblib.dump(metadata, os.path.join(model_dir, "tasks_metadata.pkl"))
    
    print(f"FAISS index built with {len(metadata)} tasks.")
    print(f"Saved to {os.path.join(model_dir, 'tasks.faiss')}")

if __name__ == "__main__":
    build_faiss()

