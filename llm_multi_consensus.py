import os
import json
import requests
from typing import Tuple, Dict, List

def get_providers_from_env() -> Dict[str, str]:
    providers = {}
    if os.getenv('OPENAI_API_KEY'):
        providers['openai'] = os.getenv('OPENAI_API_KEY')
    if os.getenv('LLM_API_URL'):
        providers['local'] = os.getenv('LLM_API_URL')
    if os.getenv('LLM_API_KEY') and os.getenv('LLM_API_URL'):
        providers['local_auth'] = os.getenv('LLM_API_URL')
    return providers

def ask_openai(prompt_obj, model='gpt-4o-mini') -> Tuple[str, float]:
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return "HOLD", 0.0
    aggression = os.getenv('LLM_AGGRESSIVENESS', '')
    style = os.getenv('LLM_PROMPT_STYLE', '')
    system_msg = "You are a strict quant assistant. Output only valid json with keys decision and confidence"
    if aggression:
        system_msg = system_msg + " Be more aggressive when looking for entries. aggressiveness=" + aggression
    if style:
        system_msg = system_msg + " prompt_style=" + style
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": json.dumps(prompt_obj)}
    ]
    body = {"model": model, "messages": messages, "max_tokens": 200, "temperature": 0}
    try:
        r = requests.post(url, headers=headers, json=body, timeout=30)
        if r.status_code != 200:
            return "HOLD", 0.0
        txt = r.json()["choices"][0]["message"]["content"]
        obj = json.loads(txt)
        decision = obj.get("decision", "HOLD")
        confidence = float(obj.get("confidence", 0.0))
        return decision.upper(), max(0.0, min(1.0, confidence))
    except Exception:
        try:
            txt = r.text.upper()
            if "LONG" in txt:
                return "LONG", 0.6
            if "SHORT" in txt:
                return "SHORT", 0.6
        except Exception:
            pass
        return "HOLD", 0.0

def ask_local(prompt_obj) -> Tuple[str, float]:
    url = os.getenv('LLM_API_URL')
    if not url:
        return "HOLD", 0.0
    headers = {}
    if os.getenv('LLM_API_KEY'):
        headers['Authorization'] = f"Bearer {os.getenv('LLM_API_KEY')}"
    try:
        r = requests.post(url, json=prompt_obj, headers=headers, timeout=30)
        if r.status_code != 200:
            return "HOLD", 0.0
        j = r.json()
        decision = j.get("decision", "HOLD")
        confidence = float(j.get("confidence", 0.0))
        return decision.upper(), max(0.0, min(1.0, confidence))
    except Exception:
        return "HOLD", 0.0

def ask_provider(provider_name: str, symbol: str, latest_bar: dict) -> Tuple[str, float]:
    prompt = {
        "instruction": "Given the provided latest bar and indicators decide one of LONG SHORT HOLD and return a json object with keys decision and confidence where confidence is 0.0 to 1.0",
        "symbol": symbol,
        "latest": latest_bar
    }
    if provider_name == 'openai':
        model = os.getenv('LLM_MODEL', 'gpt-4o-mini')
        return ask_openai(prompt, model=model)
    if provider_name in ('local', 'local_auth'):
        return ask_local(prompt)
    return "HOLD", 0.0

def provider_default_weight(name: str) -> float:
    if name == 'openai':
        return 1.0
    if name.startswith('local'):
        return 0.8
    return 0.5

def weight_from_env(name: str) -> float:
    key = f"LLM_WEIGHT_{name.upper()}"
    try:
        v = float(os.getenv(key, ''))
        return v if v > 0 else provider_default_weight(name)
    except Exception:
        return provider_default_weight(name)

def consensus_decision(symbol: str, latest_bar: dict) -> Tuple[str, float, List[Dict]]:
    providers = get_providers_from_env()
    if not providers:
        return "HOLD", 0.0, []
    scores = {}
    breakdown = []
    total_weight = 0.0
    for name in providers.keys():
        weight = weight_from_env(name)
        total_weight += weight
        decision, conf = ask_provider(name, symbol, latest_bar)
        breakdown.append({"provider": name, "decision": decision, "confidence": conf, "weight": weight})
        scores.setdefault(decision, 0.0)
        scores[decision] += conf * weight
    best = max(scores.items(), key=lambda x: x[1])
    best_score = best[1]
    final_decision = best[0]
    norm_conf = best_score / total_weight if total_weight > 0 else 0.0
    norm_conf = max(0.0, min(1.0, norm_conf))
    return final_decision, norm_conf, breakdown
