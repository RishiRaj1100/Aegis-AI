import asyncio
import httpx
import sys
import os
from config.settings import get_settings

async def test_ollama():
    settings = get_settings()
    base_url = settings.OLLAMA_BASE_URL
    model = settings.OLLAMA_MODEL
    
    print(f"Testing Ollama Connection at {base_url} using model '{model}'...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Check health
            print("Checking tags...")
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                print(f"Available models: {models}")
                if not any(m.startswith(model) for m in models):
                    print(f"WARNING: Model '{model}' not found. You need to run: docker exec aegis-ollama ollama pull {model}")
            else:
                print(f"FAILURE: Ollama returned status {response.status_code}")
                return

            # 2. Test chat
            print(f"Testing chat with model '{model}'...")
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": "Say hello in one word."}
                ],
                "stream": False
            }
            
            response = await client.post(f"{base_url}/api/chat", json=payload, timeout=60.0)
            if response.status_code == 200:
                print(f"SUCCESS: Ollama responded: {response.json()['message']['content']}")
            else:
                print(f"FAILURE: Chat failed with status {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"FAILURE: Could not connect to Ollama: {e}")
        print("Make sure the Docker container is running (docker-compose up -d)")

if __name__ == "__main__":
    asyncio.run(test_ollama())
