import os
import json
import logging
import requests

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
LIVE_ORDERS = os.getenv("LIVE_ORDERS", "False").lower() in ("1", "true", "yes")

def _headers():
    return {
        "APCA-API-KEY-ID": ALPACA_API_KEY or "",
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY or "",
        "Content-Type": "application/json"
    }

def create_alpaca_order(symbol, side, qty, limit_price=None, dry_run=True, short=False, asset_class="us_equity"):
    if dry_run or not LIVE_ORDERS:
        return {"status": "dry_run", "symbol": symbol, "side": side, "qty": qty, "limit_price": limit_price, "short": short}
    
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        return {"status": "failed", "error": "ALPACA_API_KEY or ALPACA_SECRET_KEY not set"}
    
    order_type = "market" if limit_price is None else "limit"
    
    payload = {
        "symbol": symbol,
        "qty": str(qty),
        "side": side,
        "type": order_type,
        "time_in_force": "day"
    }
    
    if limit_price is not None:
        payload["limit_price"] = str(limit_price)
    
    if asset_class == "crypto":
        payload["asset_class"] = "crypto"
        payload["time_in_force"] = "gtc"

    url = f"{ALPACA_BASE_URL.rstrip('/')}/v2/orders"
    
    try:
        h = _headers()
        resp = requests.post(url, json=payload, headers=h, timeout=15)
        try:
            data = resp.json()
        except Exception:
            data = resp.text
            
        if 200 <= resp.status_code < 300:
            return {"status": "placed", "id": data.get("id"), "response": data}
        return {"status": "error", "code": resp.status_code, "response": data}
    except Exception as e:
        logging.error("Alpaca execution exception: %s", e)
        return {"status": "failed", "error": str(e)}
