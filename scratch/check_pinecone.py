import os
import sys
import asyncio
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# Load environment variables
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

def check_pinecone():
    print(f"--- Pinecone Diagnostic ---")
    if not PINECONE_API_KEY or "your_" in PINECONE_API_KEY:
        print("❌ Error: PINECONE_API_KEY is missing or invalid in .env")
        return
    
    print(f"API Key found: {PINECONE_API_KEY[:8]}...{PINECONE_API_KEY[-4:]}")
    
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        print("OK: Pinecone client initialized.")
        
        indexes = pc.list_indexes()
        print(f"OK: Connection successful. Available indexes: {[idx.name for idx in indexes]}")
        
        if PINECONE_INDEX_NAME in [idx.name for idx in indexes]:
            print(f"OK: Index '{PINECONE_INDEX_NAME}' exists and is accessible.")
            index = pc.Index(PINECONE_INDEX_NAME)
            stats = index.describe_index_stats()
            print(f"STATS: Index Stats: Total Vector Count: {stats['total_vector_count']}")
        else:
            print(f"WARNING: Index '{PINECONE_INDEX_NAME}' NOT found in your account.")
            
    except Exception as e:
        print(f"ERROR: Pinecone Connection Failed: {str(e)}")

if __name__ == "__main__":
    check_pinecone()
