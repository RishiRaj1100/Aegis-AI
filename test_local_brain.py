import asyncio
import logging
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from services.local_inference_service import get_local_inference_service

logging.basicConfig(level=logging.INFO)

async def test():
    print("Initializing Local Aegis Brain...")
    service = get_local_inference_service()
    
    if not service.enabled:
        print("Local model is disabled in .env. Please check USE_LOCAL_MODEL.")
        return

    print(f"Loading model from: {service.model_path}")
    
    try:
        response = await service.chat(
            system_prompt="Analyze task risk.",
            user_message="Task: Launch health supplement brand in India. Deadline: 60 days. Complexity: 0.85.",
            max_tokens=100
        )
        print("\n--- Model Response ---")
        print(response)
        print("----------------------\n")
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test())
