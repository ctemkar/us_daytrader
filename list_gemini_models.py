import os
import requests

key = os.getenv("GEMINI_API_KEY")
if not key:
    print("❌ GEMINI_API_KEY not found in env")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
resp = requests.get(url)
if resp.status_code == 200:
    data = resp.json()
    print("✅ Available Gemini Models:")
    for model in data.get("models", []):
        print(" -", model.get("name"))
else:
    print(f"❌ Gemini Error {resp.status_code}: {resp.text}")
