import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from services.retrieval_service import get_retrieval_service

async def test_similarity():
    print("Testing Similarity Metadata Storage...")
    retrieval = get_retrieval_service()
    
    # Add a task with full metadata
    test_task = "Build a React dashboard with Tailwind CSS"
    metadata = {
        "task_id": "TEST_001",
        "success": True,
        "confidence": 85.0,
        "execution_plan": "Step 1: Init project. Step 2: Install Tailwind.",
        "research_insights": "React is popular. Tailwind is fast.",
        "recommended_resources": ["https://reactjs.org", "https://tailwindcss.com"]
    }
    
    retrieval.add_task(test_task, metadata)
    print(f"Index total: {retrieval.index.ntotal}")
    print(f"Metadata total: {len(retrieval.metadata)}")
    
    # Search for it
    results = retrieval.search_similar(test_task, top_k=1)
    
    if not results:
        print("Error: No results found.")
        return
        
    res = results[0]
    print("\nSearch Result:")
    print(f"  Goal: {res.get('goal')}")
    print(f"  Plan: {res.get('execution_plan')}")
    print(f"  Insights: {res.get('insights')}")
    print(f"  Resources: {res.get('resources')}")
    
    # Assertions
    assert res.get('execution_plan') == metadata['execution_plan']
    assert res.get('insights') == metadata['research_insights']
    assert len(res.get('resources')) == 2
    
    print("\nSimilarity Metadata Test Passed!")

if __name__ == "__main__":
    asyncio.run(test_similarity())
