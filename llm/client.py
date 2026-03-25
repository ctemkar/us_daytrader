import os
import asyncio
import aiohttp
import json
import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def load_local_env(path=".env"):
    p = Path(path)
    if not p.exists():
        return
    try:
        text = p.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1]
            if k and v and os.environ.get(k) is None:
                os.environ[k] = v
    except Exception as e:
        logging.error("env load error %s", e)

load_local_env()

class LLMClient:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.route_llm_key = os.getenv("ROUTE_LLM_API_KEY")
        self.grok_key = os.getenv("GROK_API_KEY")
        self.local_url = os.getenv("LLM_LOCAL_URL")
        self.gemini_model = os.getenv("GEMINI_MODEL", "google/gemini-pro")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek/deepseek-chat")
        self.grok_model = os.getenv("GROK_MODEL", "grok-1")
        self.timeout = int(os.getenv("LLM_TIMEOUT", "15"))
        self.max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
        self.base_backoff = float(os.getenv("LLM_BACKOFF", "1.0"))
        self._session = None
        self.fail_counts = {"openai": 0, "gemini": 0, "deepseek": 0, "grok": 0, "local": 0}
        self.disabled = set()
        providers = []
        if self.openai_key: providers.append("openai")
        if self.route_llm_key: providers.append("route_llm")
        if self.grok_key: providers.append("grok")
        if self.local_url: providers.append("local")
        logging.info("LLMClient initialized providers %s", providers)

    async def _get_session(self):
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        if self._session is not None:
            try:
                await self._session.close()
            except Exception as e:
                logging.error("session close error %s", e)
            self._session = None
            logging.info("LLMClient session closed")

    async def _request_with_retries(self, name, method, url, headers, json_body):
        if name in self.disabled:
            return {"provider": name, "decision": "HOLD", "confidence": 0.0, "raw": "disabled"}
        attempt = 0
        while attempt <= self.max_retries:
            try:
                s = await self._get_session()
                async with s.request(method, url, headers=headers, json=json_body) as resp:
                    raw = await resp.text()
                    if 200 <= resp.status < 300:
                        self.fail_counts[name] = 0
                        return {"provider": name, "status": resp.status, "raw": raw}
                    else:
                        self.fail_counts[name] += 1
                        if self.fail_counts[name] >= 3:
                            self.disabled.add(name)
                            logging.error("%s disabled after 3 failures", name)
                        if resp.status == 429 or resp.status >= 500:
                            attempt += 1
                            await asyncio.sleep(self.base_backoff * (2 ** attempt))
                            continue
                        return {"provider": name, "status": resp.status, "raw": raw}
            except Exception as e:
                self.fail_counts[name] += 1
                if self.fail_counts[name] >= 3:
                    self.disabled.add(name)
                attempt += 1
                await asyncio.sleep(self.base_backoff * (2 ** attempt))
        return {"provider": name, "decision": "HOLD", "confidence": 0.0, "raw": "failed"}

    async def _parse_chat_response(self, name, raw_text):
        try:
            res = json.loads(raw_text)
            content = res.get("choices", [{}])[0].get("message", {}).get("content", "")
            m = re.search(r"\{.*\}", content, re.DOTALL)
            if not m: return {"provider": name, "decision": "HOLD", "confidence": 0.0, "raw": content}
            data = json.loads(m.group())
            return {"provider": name, "decision": data.get("decision", "HOLD").upper(), "confidence": float(data.get("confidence", 0.0)), "raw": content}
        except Exception as e:
            return {"provider": name, "decision": "HOLD", "confidence": 0.0, "raw": raw_text}

    async def _call_openai(self, symbol, summary):
        if not self.openai_key: return {"provider": "openai", "decision": "HOLD", "confidence": 0.0, "raw": None}
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
        system_msg = "You are an aggressive intraday quant trader. Decide BUY, SELL, or HOLD. Return JSON only."
        user_msg = f"Symbol {symbol} data: {summary}. Return JSON: {'{'}\"decision\":\"BUY\",\"confidence\":0.8,\"reason\":\"...\"{'}'}"
        body = {"model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"), "messages": [{"role":"system","content":system_msg}, {"role":"user","content":user_msg}], "temperature": 0.2}
        resp = await self._request_with_retries("openai", "POST", url, headers, body)
        if resp.get("status") == 200: return await self._parse_chat_response("openai", resp["raw"])
        return {"provider": "openai", "decision": "HOLD", "confidence": 0.0, "raw": resp.get("raw")}

    async def _call_route_model(self, name, model, symbol, summary):
        if not self.route_llm_key: return {"provider": name, "decision": "HOLD", "confidence": 0.0, "raw": None}
        url = "https://routellm.abacus.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.route_llm_key}", "Content-Type": "application/json"}
        system_msg = "You are an aggressive intraday quant trader. Decide BUY, SELL, or HOLD. Return JSON only."
        user_msg = f"Symbol {symbol} data: {summary}. Return JSON: {'{'}\"decision\":\"BUY\",\"confidence\":0.8,\"reason\":\"...\"{'}'}"
        body = {"model": model, "messages": [{"role":"system","content":system_msg}, {"role":"user","content":user_msg}], "temperature": 0.2}
        resp = await self._request_with_retries(name, "POST", url, headers, body)
        if resp.get("status") == 200: return await self._parse_chat_response(name, resp["raw"])
        return {"provider": name, "decision": "HOLD", "confidence": 0.0, "raw": resp.get("raw")}

    async def _call_grok(self, symbol, summary):
        if not self.grok_key: return {"provider": "grok", "decision": "HOLD", "confidence": 0.0, "raw": None}
        url = "https://api.x.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.grok_key}", "Content-Type": "application/json"}
        system_msg = "You are an aggressive intraday quant trader. Decide BUY, SELL, or HOLD. Return JSON only."
        user_msg = f"Symbol {symbol} data: {summary}. Return JSON: {'{'}\"decision\":\"BUY\",\"confidence\":0.8,\"reason\":\"...\"{'}'}"
        body = {"model": self.grok_model, "messages": [{"role":"system","content":system_msg}, {"role":"user","content":user_msg}], "temperature": 0.2}
        resp = await self._request_with_retries("grok", "POST", url, headers, body)
        if resp.get("status") == 200: return await self._parse_chat_response("grok", resp["raw"])
        return {"provider": "grok", "decision": "HOLD", "confidence": 0.0, "raw": resp.get("raw")}

    async def get_consensus(self, symbol, summary):
        tasks = []
        if self.openai_key and "openai" not in self.disabled:
            tasks.append(self._call_openai(symbol, summary))
        if self.route_llm_key:
            if "gemini" not in self.disabled:
                tasks.append(self._call_route_model("gemini", self.gemini_model, symbol, summary))
            if "deepseek" not in self.disabled:
                tasks.append(self._call_route_model("deepseek", self.deepseek_model, symbol, summary))
        if self.grok_key and "grok" not in self.disabled:
            tasks.append(self._call_grok(symbol, summary))

        if not tasks: return {"decision": "HOLD", "confidence": 0.0, "providers": [], "votes": [0, 0, 1], "raw": []}
        results = await asyncio.gather(*tasks, return_exceptions=True)
        parsed = []
        for r in results:
            if isinstance(r, Exception): parsed.append({"provider": "err", "decision": "HOLD", "confidence": 0.0, "raw": str(r)})
            else: parsed.append(r)

        buy = sell = hold = 0
        details = []
        total_conf = 0.0
        count = 0
        for p in parsed:
            d = (p.get("decision") or "HOLD").upper()
            c = float(p.get("confidence") or 0.0)
            name = p.get("provider", "unknown")
            details.append(f"{name}-{d}({c:.3f})")
            if d == "BUY": buy += 1
            elif d == "SELL": sell += 1
            else: hold += 1
            total_conf += c
            count += 1
        avg_conf = round(total_conf / count, 3) if count else 0.0
        final = "HOLD"
        if buy > sell and buy > hold: final = "BUY"
        elif sell > buy and sell > hold: final = "SELL"
        logging.info("RESULT %s -> %s (conf: %.3f) details: %s", symbol, final, avg_conf, details)
        return {"decision": final, "confidence": avg_conf, "providers": details, "votes": [buy, sell, hold], "raw": parsed}
