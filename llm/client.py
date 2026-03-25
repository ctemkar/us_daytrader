import os
import asyncio
import aiohttp
import json
import re
import statistics
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def load_local_env(path=".env"):
    p = Path(path)
    if not p.exists():
        return
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        elif val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        if key and val and os.environ.get(key) is None:
            os.environ[key] = val

load_local_env()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL")
GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_API_URL = os.getenv("GROK_API_URL")
REQUEST_TIMEOUT = float(os.getenv("LLM_REQUEST_TIMEOUT", "12"))
OPENAI_WEIGHT = float(os.getenv("OPENAI_WEIGHT", "1.0"))
DEEPSEEK_WEIGHT = float(os.getenv("DEEPSEEK_WEIGHT", "1.0"))
GROK_WEIGHT = float(os.getenv("GROK_WEIGHT", "1.0"))
CONFIDENCE_THRESHOLD = float(os.getenv("LLM_CONF_THRESHOLD", "0.65"))
TIE_MARGIN = float(os.getenv("LLM_TIE_MARGIN", "1.05"))

def _extract_decision_and_confidence(text):
    if not text:
        return "HOLD", 0.0, ""
    t = text.strip()
    m = re.search(r'\b(BUY|SELL|HOLD|SHORT|COVER)\b', t, flags=re.IGNORECASE)
    decision = m.group(1).upper() if m else None
    c = None
    m2 = re.search(r'([01](?:\.[0-9]{1,3})?)', t)
    if m2:
        try:
            v = float(m2.group(1))
            if 0.0 <= v <= 1.0:
                c = v
        except Exception:
            c = None
    if c is None:
        m3 = re.search(r'(\d{1,3})\s?%', t)
        if m3:
            try:
                pct = float(m3.group(1))
                c = max(0.0, min(1.0, pct / 100.0))
            except Exception:
                c = 0.0
    if c is None:
        c = 0.5
    reason = ""
    try:
        j = json.loads(t)
        if isinstance(j, dict):
            decision = j.get("decision", decision)
            c = float(j.get("confidence", c))
            reason = j.get("reason", "") or reason
    except Exception:
        reason = t
    if decision not in ("BUY", "SELL", "HOLD", "SHORT", "COVER"):
        low = t.lower()
        b = low.count("buy")
        s = low.count("sell")
        h = low.count("hold")
        shortc = low.count("short")
        coverc = low.count("cover")
        counts = {"BUY": b, "SELL": s, "HOLD": h, "SHORT": shortc, "COVER": coverc}
        decision = max(counts.items(), key=lambda x: x[1])[0]
    try:
        c = float(c)
    except Exception:
        c = 0.5
    c = max(0.0, min(1.0, c))
    return decision, c, reason

class LLMClient:
    def __init__(self):
        self.openai_key = OPENAI_API_KEY
        self.openai_model = OPENAI_MODEL
        self.deepseek_key = DEEPSEEK_API_KEY
        self.deepseek_url = DEEPSEEK_API_URL
        self.grok_key = GROK_API_KEY
        self.grok_url = GROK_API_URL
        self.timeout = REQUEST_TIMEOUT
        self._session = None
        logging.info("LLMClient init openai=%s deepseek=%s deepseek_url=%s grok=%s grok_url=%s",
                     bool(self.openai_key), bool(self.deepseek_key), bool(self.deepseek_url), bool(self.grok_key), bool(self.grok_url))
        if self.openai_key and self.openai_key.startswith("put_your"):
            logging.warning("OPENAI_API_KEY looks like a placeholder value")
    async def _session_ctx(self):
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None
    async def _call_openai(self, symbol, summary):
        provider = "openai"
        if not self.openai_key:
            logging.info("openai skipped no key")
            return {"provider": provider, "status": "skipped", "raw": None, "error": "no key", "weight": OPENAI_WEIGHT}
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
        prompt = [
            {"role": "system", "content": "You are a concise trading assistant. Output only JSON with keys decision confidence reason where decision is BUY SELL HOLD SHORT or COVER and confidence is 0.0-1.0"},
            {"role": "user", "content": f"Symbol: {symbol}\nContext: {summary}\nAnswer in JSON with decision confidence reason"}
        ]
        body = {"model": self.openai_model, "messages": prompt, "max_tokens": 200, "temperature": 0.0}
        start = time.perf_counter()
        try:
            s = await self._session_ctx()
            async with s.post(url, json=body, headers=headers) as resp:
                elapsed = time.perf_counter() - start
                txt = await resp.text()
                status = resp.status
                logging.info("openai status %s latency %.3f s", status, elapsed)
                if status != 200:
                    logging.info("openai raw error %s", txt[:1000])
                    return {"provider": provider, "status": "error", "raw": txt, "error": f"status {status}", "weight": OPENAI_WEIGHT}
                try:
                    j = json.loads(txt)
                    choice = j.get("choices", [{}])[0]
                    message = choice.get("message", {}).get("content", "")
                    logging.info("openai raw response %s", (message or txt)[:1000])
                    return {"provider": provider, "status": "ok", "raw": message or txt, "weight": OPENAI_WEIGHT}
                except Exception:
                    logging.info("openai parse fail raw %s", txt[:1000])
                    return {"provider": provider, "status": "ok", "raw": txt, "weight": OPENAI_WEIGHT}
        except Exception as e:
            logging.error("openai exception %s", e)
            return {"provider": provider, "status": "error", "raw": None, "error": str(e), "weight": OPENAI_WEIGHT}
    async def _call_deepseek(self, symbol, summary):
        provider = "deepseek"
        if not self.deepseek_key or not self.deepseek_url:
            logging.info("deepseek skipped no key or url")
            return {"provider": provider, "status": "skipped", "raw": None, "error": "no key or url", "weight": DEEPSEEK_WEIGHT}
        url = self.deepseek_url
        headers = {"Authorization": f"Bearer {self.deepseek_key}", "Content-Type": "application/json"}
        payload = {"symbol": symbol, "context": summary}
        start = time.perf_counter()
        try:
            s = await self._session_ctx()
            async with s.post(url, json=payload, headers=headers) as resp:
                elapsed = time.perf_counter() - start
                txt = await resp.text()
                status = resp.status
                logging.info("deepseek status %s latency %.3f s", status, elapsed)
                if status != 200:
                    logging.info("deepseek raw error %s", txt[:1000])
                    return {"provider": provider, "status": "error", "raw": txt, "error": f"status {status}", "weight": DEEPSEEK_WEIGHT}
                return {"provider": provider, "status": "ok", "raw": txt, "weight": DEEPSEEK_WEIGHT}
        except Exception as e:
            logging.error("deepseek exception %s", e)
            return {"provider": provider, "status": "error", "raw": None, "error": str(e), "weight": DEEPSEEK_WEIGHT}
    async def _call_grok(self, symbol, summary):
        provider = "grok"
        if not self.grok_key or not self.grok_url:
            logging.info("grok skipped no key or url")
            return {"provider": provider, "status": "skipped", "raw": None, "error": "no key or url", "weight": GROK_WEIGHT}
        url = self.grok_url
        headers = {"Authorization": f"Bearer {self.grok_key}", "Content-Type": "application/json"}
        payload = {"symbol": symbol, "summary": summary}
        start = time.perf_counter()
        try:
            s = await self._session_ctx()
            async with s.post(url, json=payload, headers=headers) as resp:
                elapsed = time.perf_counter() - start
                txt = await resp.text()
                status = resp.status
                logging.info("grok status %s latency %.3f s", status, elapsed)
                if status != 200:
                    logging.info("grok raw error %s", txt[:1000])
                    return {"provider": provider, "status": "error", "raw": txt, "error": f"status {status}", "weight": GROK_WEIGHT}
                return {"provider": provider, "status": "ok", "raw": txt, "weight": GROK_WEIGHT}
        except Exception as e:
            logging.error("grok exception %s", e)
            return {"provider": provider, "status": "error", "raw": None, "error": str(e), "weight": GROK_WEIGHT}
    async def get_consensus(self, symbol, summary):
        tasks = []
        if self.openai_key:
            tasks.append(self._call_openai(symbol, summary))
        if self.deepseek_key and self.deepseek_url:
            tasks.append(self._call_deepseek(symbol, summary))
        if self.grok_key and self.grok_url:
            tasks.append(self._call_grok(symbol, summary))
        if not tasks:
            return {"decision": "HOLD", "confidence": 0.0, "reason": "no providers configured", "votes": [], "provider_count": 0, "providers": []}
        done = await asyncio.gather(*tasks, return_exceptions=True)
        parsed = []
        providers_info = []
        for r in done:
            if isinstance(r, Exception):
                providers_info.append({"provider": "unknown", "status": "error", "raw": None, "error": str(r), "decision": "HOLD", "confidence": 0.0, "reason": ""})
                continue
            rec = r or {}
            provider = rec.get("provider", "unknown")
            status = rec.get("status", "error")
            raw = rec.get("raw")
            weight = float(rec.get("weight", 1.0))
            error = rec.get("error")
            if status == "ok" and raw:
                dec, conf, reason = _extract_decision_and_confidence(raw)
                parsed.append({"provider": provider, "decision": dec, "confidence": conf, "reason": reason, "raw": raw, "weight": weight})
                providers_info.append({"provider": provider, "status": "ok", "raw": raw, "decision": dec, "confidence": conf, "reason": reason, "weight": weight})
            else:
                providers_info.append({"provider": provider, "status": status, "raw": raw, "error": error, "decision": "HOLD", "confidence": 0.0, "reason": error or "", "weight": weight})
        provider_ok_count = sum(1 for p in providers_info if p.get("status") == "ok")
        if provider_ok_count == 0:
            return {"decision": "HOLD", "confidence": 0.0, "reason": "no successful providers", "votes": [], "provider_count": len(providers_info), "providers": providers_info, "raw": parsed}
        scores = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0, "SHORT": 0.0, "COVER": 0.0}
        counts = {"BUY": 0, "SELL": 0, "HOLD": 0, "SHORT": 0, "COVER": 0}
        for p in parsed:
            d = p["decision"]
            c = float(p["confidence"])
            w = float(p.get("weight", 1.0))
            scores[d] = scores.get(d, 0.0) + w * c
            counts[d] = counts.get(d, 0) + 1
        final_decision = max(scores.items(), key=lambda x: x[1])[0]
        top_score = scores[final_decision]
        other_scores = [v for k,v in scores.items() if k != final_decision]
        if other_scores and top_score < max(other_scores) * TIE_MARGIN:
            final_decision = "HOLD"
        buy_score = scores.get("BUY", 0.0) + scores.get("SHORT", 0.0)
        sell_score = scores.get("SELL", 0.0) + scores.get("COVER", 0.0)
        if final_decision == "HOLD":
            if buy_score >= CONFIDENCE_THRESHOLD:
                final_decision = "BUY"
            elif sell_score >= CONFIDENCE_THRESHOLD:
                final_decision = "SELL"
        confidences = [p["confidence"] for p in parsed if p["decision"] == final_decision]
        if not confidences:
            confidences = [p["confidence"] for p in parsed]
        avg_conf = float(statistics.mean(confidences)) if confidences else 0.0
        reasons = [p["reason"] for p in parsed if p.get("reason")]
        reason_combined = " | ".join(reasons[:3])
        votes_list = [counts["BUY"], counts["SELL"], counts["HOLD"], counts["SHORT"], counts["COVER"]]
        return {
            "decision": final_decision,
            "confidence": round(avg_conf, 3),
            "reason": reason_combined,
            "votes": votes_list,
            "provider_count": len(providers_info),
            "providers": providers_info,
            "raw": parsed
        }
