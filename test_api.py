import requests
import json

url = "http://127.0.0.1:8000/goal"
payload = {
    "goal": "I want to launch a health supplement brand in India selling immunity-boosting products targeting mothers aged 25–45.",
    "language": "en-IN"
}

try:
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
