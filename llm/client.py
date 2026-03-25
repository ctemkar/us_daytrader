import os
import json
import asyncio
import logging
import requests
from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

class LLMClient:
    def __init__(self):
        self.providers = ["openai", "grok"]
        self.failures = {p: 0 for p in self.providers}
        self.disabled = {p: False for p in self.providers}
        logging.info("LLMClient initialized providers %s", self.providers)

    async def get_consensus(self, symbol, summary):
        tasks = []
        if not self.disabled["openai"]:
            tasks.append(self._query_provider("openai", symbol, summary))
        if not self.disabled["grok"]:
            tasks.append(self._query_provider("grok", symbol, summary))
        
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
            "providers": [f"{r['p']}-{r['decision']}({r['confidence']:.3f})" for r in valid]
        }

    async def _query_provider(self, provider, symbol, summary):
        try:
            prompt = f"Analyze {symbol}: {summary}. Return JSON: {{\"decision\": \"BUY|SELL|HOLD\", \"confidence\": 0.0-1.0, \"reason\": \"...\"}}"
            
            if provider == "openai":
                url = "https://api.openai.com/v1/chat/completions"
                key = os.getenv("OPENAI_API_KEY")
                model = "gpt-4o"
            else:
                url = "https://api.x.ai/v1/chat/completions"
                key = os.getenv("GROK_API_KEY")
                model = "grok-beta"

            if not key:
                return None

            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}
            }

            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code != 200:
                logging.error("%s Error %s: %s", provider, resp.status_code, resp.text)
                self.failures[provider] += 1
                if self.failures[provider] >= 5:
                    self.disabled[provider] = True
                return None

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logging.info("FORECAST %s for %s: %s", provider, symbol, content)
            res = json.loads(content)
            res["p"] = provider
            return res
        except Exception as e:
            logging.error("%s Exception: %s", provider, e)
            return None

    async def close(self):
        pass
