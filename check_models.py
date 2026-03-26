import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

async def check_openai():
    key = os.getenv("OPENAI_API_KEY")
    if not key: return print("OpenAI: No Key")
    url = "https://api.openai.com/v1/models"
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers={"Authorization": f"Bearer {key}"}) as r:
            data = await r.json()
            models = [m['id'] for m in data.get('data', []) if 'gpt' in m['id']]
            print(f"OpenAI Models: {models[:5]}")

async def check_grok():
    key = os.getenv("GROK_API_KEY")
    if not key: return print("Grok: No Key")
    url = "https://api.x.ai/v1/models"
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers={"Authorization": f"Bearer {key}"}) as r:
            data = await r.json()
            models = [m['id'] for m in data.get('data', [])]
            print(f"Grok Models: {models}")

async def check_deepseek():
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key: return print("DeepSeek: No Key")
    url = "https://api.deepseek.com/models"
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers={"Authorization": f"Bearer {key}"}) as r:
            data = await r.json()
            models = [m['id'] for m in data.get('data', [])]
            print(f"DeepSeek Models: {models}")

async def check_gemini():
    key = os.getenv("GEMINI_API_KEY")
    if not key: return print("Gemini: No Key")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            data = await r.json()
            models = [m['name'].replace('models/', '') for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            print(f"Gemini Models: {models[:5]}")

async def main():
    print("--- API DIAGNOSTICS ---")
    await asyncio.gather(check_openai(), check_grok(), check_deepseek(), check_gemini())

if __name__ == "__main__":
    asyncio.run(main())
