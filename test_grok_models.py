import os
import requests

key = os.getenv("GROK_API_KEY")
if not key:
    print("❌ GROK_API_KEY not found in env")
    exit(1)

url = "https://api.x.ai/v1/models"
headers = {"Authorization": f"Bearer {key}"}

resp = requests.get(url, headers=headers)
if resp.status_code == 200:
    models = resp.json().get("data", [])
    print("✅ Available Grok Models:")
    for m in models:
        print(f" - {m['id']}")
else:
    print(f"❌ Grok Error {resp.status_code}: {resp.text}")
