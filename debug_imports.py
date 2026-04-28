import sys
import os

modules = [
    "logging",
    "json",
    "datetime",
    "typing",
    "asyncio",
    "fastapi",
    "pydantic",
    "pydantic_settings",
    "motor",
    "pymongo",
    "redis",
    "pinecone",
    "openai",
    "sentence_transformers",
    "jwt",
    "bcrypt",
    "dotenv",
    "uvicorn",
    "xgboost",
    "pandas",
    "sklearn",
    "joblib",
    "shap",
    "faiss",
]

for m in modules:
    try:
        print(f"Importing {m}...")
        __import__(m)
        print(f"Done.")
    except Exception as e:
        print(f"FAILED to import {m}: {e}")
