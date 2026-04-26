import os
import httpx
from dotenv import load_dotenv

load_dotenv()

def check_openrouter():
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct")
    
    print(f"--- OpenRouter Diagnostic ---")
    if not api_key or "your_" in api_key:
        print("ERROR: OPENROUTER_API_KEY is missing or invalid.")
        return
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say hello world in one word"}],
        "max_tokens": 10
    }
    
    try:
        response = httpx.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=20.0)
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"OK: Connection successful. Model responded: {content.strip()}")
        else:
            print(f"ERROR: OpenRouter returned {response.status_code}: {response.text}")
    except Exception as e:
        print(f"ERROR: OpenRouter Connection Failed: {str(e)}")

if __name__ == "__main__":
    check_openrouter()
