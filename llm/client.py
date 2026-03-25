import os
import json
import asyncio
import logging
import requests
from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

class LLMClient:
    def __init__(self):
        self.providers = ["openai", "grok", "deepseek", "gemini", "abacus"]
        self.failures = {p: 0 for p in self.providers}
        self.disabled = {p: False for p in self.providers}
        logging.info("LLMClient initialized with 5 providers: %s", self.providers)

    async def get_consensus(self, symbol, summary):
        tasks = []
        for p in self.providers:
            if not self.disabled[p]:
                tasks.append(self._query_provider(p, symbol, summary))
        
        results = await asyncio.gather(*tasks)
        valid = [r for r in results if r]
        
        if not valid:
            return {"decision": "HOLD", "confidence": 0.0, "votes": [0, 0, 1], "providers": []}

        buys = len([r for r in valid if r["decision"] == "BUY"])
        sells = len([r for r in valid if r["decision"] == "SELL"])
        holds = len([r for r in valid if r["decision"] == "HOLD"])
        
        total = len(valid)
        if buys > sells and buys > holds:
            decision = "BUY"
            conf = sum(r["confidence"] for r in valid if r["decision"] == "BUY") / total
        elif sells > buys and sells > holds:
            decision = "SELL"
            conf = sum(r["confidence"] for r in valid if r["decision"] == "SELL") / total
        else:
            decision = "HOLD"
            conf = 0.0

        return {
            "decision": decision,
            "confidence": round(conf, 3),
            "votes": [buys, sells, holds],
            "providers": [f"{r['p']}-{r['decision']}({r['confidence']:.2f})" for r in valid]
        }

    async def _query_provider(self, provider, symbol, summary):
        try:
            prompt = f"Analyze {symbol} stock: {summary}. Return JSON: {{\"decision\": \"BUY|SELL|HOLD\", \"confidence\": 0.0-1.0, \"reason\": \"...\"}}"
            
            url = ""
            headers = {}
            payload = {}
            key = ""

            if provider == "openai":
                url = "https://api.openai.com/v1/chat/completions"
                key = os.getenv("OPENAI_API_KEY")
                payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}
                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            
            elif provider == "grok":
                url = "https://api.x.ai/v1/chat/completions"
                key = os.getenv("GROK_API_KEY")
                payload = {"model": "grok-4-1-fast-reasoning", "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}
                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

            elif provider == "deepseek":
                url = "https://api.deepseek.com/v1/chat/completions"
                key = os.getenv("DEEPSEEK_API_KEY")
                payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}
                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

            elif provider == "gemini":
                key = os.getenv("GEMINI_API_KEY")
                if not key:
                    return None
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt + " Respond with valid JSON only."}]}],
                    "generationConfig": {"response_mime_type": "application/json"}
                }
                headers = {"Content-Type": "application/json"}

            elif provider == "abacus":
                key = os.getenv("ABACUS_API_KEY")
                if not key:
                    return None
                url = "https://routellm.abacus.ai/v1/chat/completions"
                payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}]}
                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

            if not key:
                return None

            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            if resp.status_code != 200:
                logging.error("%s Error %s: %s", provider, resp.status_code, resp.text[:100])
                self.failures[provider] += 1
                if self.failures[provider] >= 3:
                    self.disabled[provider] = True
                return None

            data = resp.json()
            if provider == "gemini":
                content = data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                content = data["choices"][0]["message"]["content"]
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            res = json.loads(content)
            res["p"] = provider
            logging.info("FORECAST %s for %s: %s", provider, symbol, res["decision"])
            return res
        except Exception as e:
            logging.error("%s Exception: %s", provider, str(e)[:100])
            return None

    async def close(self):
        pass
