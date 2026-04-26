import os
import asyncio
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

async def test_pinecone():
    api_key = os.getenv("PINECONE_API_KEY")
    host = os.getenv("PINECONE_HOST")
    index_name = os.getenv("PINECONE_INDEX_NAME", "aegis-task-semantic")
    
    print(f"Testing Pinecone Connection...")
    print(f"API Key: {api_key[:10]}...")
    print(f"Host: {host}")
    print(f"Index: {index_name}")
    
    try:
        pc = Pinecone(api_key=api_key)
        
        # Check if index exists
        indexes = pc.list_indexes().names()
        print(f"Existing indexes: {indexes}")
        
        if index_name not in indexes:
            print(f"WARNING: Index '{index_name}' not found in list_indexes().")
        
        # Connect to index
        index = pc.Index(host=host)
        stats = index.describe_index_stats()
        print(f"Index Stats: {stats}")
        
        print("\nSUCCESS: Pinecone is working correctly!")
        
    except Exception as e:
        print(f"\nFAILURE: Pinecone error: {e}")

if __name__ == "__main__":
    asyncio.run(test_pinecone())
