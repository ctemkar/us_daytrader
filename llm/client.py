import os
import logging
import asyncio
import aiohttp
import json
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.grok_key = os.getenv("GROK_API_KEY")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

    async def get_consensus(self, symbol, summary):
        tasks = []
        providers = []
        if self.openai_key:
            tasks.append(self.query_openai(symbol, summary))
            providers.append("OpenAI")
        if self.grok_key:
            tasks.append(self.query_grok(symbol, summary))
            providers.append("Grok")
        if self.deepseek_key:
            tasks.append(self.query_deepseek(symbol, summary))
            providers.append("DeepSeek")
        if self.gemini_key:
            tasks.append(self.query_gemini(symbol, summary))
            providers.append("Gemini")

        if not tasks: return {"decision": "HOLD", "confidence": 0.0}

        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_results = {}
        for i, result in enumerate(results):
            name = providers[i]
            if isinstance(result, Exception):
                logging.error(f"LLM {name} error for {symbol}: {result}")
            else:
                logging.info(f"LLM {name} for {symbol}: decision={result['decision']} confidence={result['confidence']:.3f}")
                valid_results[name] = result
        return self.aggregate(valid_results)

    def aggregate(self, results):
        if not results: return {"decision": "HOLD", "confidence": 0.0}
        
        decisions = [res['decision'] for res in results.values()]
        confidences = [res['confidence'] for res in results.values()]
        
        # If there is any BUY or SELL with high confidence, prioritize it over HOLD
        active_signals = [res for res in results.values() if res['decision'] in ['BUY', 'SELL'] and res['confidence'] > 0.7]
        
        if active_signals:
            best_signal = max(active_signals, key=lambda x: x['confidence'])
            return {"decision": best_signal['decision'], "confidence": best_signal['confidence']}

        # Fallback to majority
        counts = {}
        for d in decisions: counts[d] = counts.get(d, 0) + 1
        maj = max(counts, key=counts.get)
        return {"decision": maj, "confidence": sum(confidences)/len(confidences)}

    async def query_openai(self, symbol, summary):
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}"}
        payload = {
            "model": "gpt-5.4-mini",
            "messages": [{"role": "system", "content": "You are an aggressive intraday scalper. Look for tiny edges."},
                         {"role": "user", "content": f"Ticker {symbol}: {summary}. Decide BUY/SELL/HOLD. JSON ONLY: {{\"decision\":\"BUY\",\"confidence\":0.9}}"}],
            "response_format": {"type": "json_object"}
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
                content = json.loads(data['choices'][0]['message']['content'])
                return {"decision": content['decision'].upper(), "confidence": float(content['confidence'])}

    async def query_grok(self, symbol, summary):
        url = "https://api.x.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.grok_key}", "Content-Type": "application/json"}
        payload = {
            "model": "grok-3",
            "messages": [{"role": "user", "content": f"Ticker {symbol}: {summary}. Aggressive scalping mode. JSON ONLY: {{\"decision\":\"BUY\",\"confidence\":0.9}}"}],
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 503: raise Exception("Grok Overloaded (503)")
                data = await resp.json()
                raw = data['choices'][0]['message']['content'].strip().replace("```json", "").replace("```", "")
                content = json.loads(raw)
                return {"decision": content['decision'].upper(), "confidence": float(content['confidence'])}

    async def query_deepseek(self, symbol, summary):
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Authorization": f"Bearer {self.deepseek_key}"}
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": f"Ticker {symbol}: {summary}. Scalping decision. JSON ONLY: {{\"decision\":\"BUY\",\"confidence\":0.9}}"}],
            "response_format": {"type": "json_object"}
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
                content = json.loads(data['choices'][0]['message']['content'])
                return {"decision": content['decision'].upper(), "confidence": float(content['confidence'])}

    async def query_gemini(self, symbol, summary):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
        payload = {
            "contents": [{"parts": [{"text": f"Ticker {symbol}: {summary}. Scalping decision. JSON ONLY: {{\"decision\":\"BUY\",\"confidence\":0.9}}"}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                raw = data['candidates'][0]['content']['parts'][0]['text'].strip().replace("```json", "").replace("```", "")
                content = json.loads(raw)
                return {"decision": content['decision'].upper(), "confidence": float(content['confidence'])}

    async def close(self): pass
