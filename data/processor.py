import os
import time
import random
import logging
from datetime import datetime, timezone
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
try:
    import yfinance as yf
    YFINANCE_OK = True
except Exception:
    YFINANCE_OK = False
class DataProcessor:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = int(os.getenv("DATA_CACHE_TTL", "5"))
    def _now(self):
        return int(time.time())
    def _from_cache(self, symbol):
        ent = self.cache.get(symbol)
        if not ent: return None
        if self._now() - ent.get("ts", 0) > self.cache_ttl: return None
        return ent.get("data")
    def fetch_latest(self, symbol):
        cached = self._from_cache(symbol)
        if cached: return cached
        if YFINANCE_OK:
            try:
                t = yf.Ticker(symbol)
                df = t.history(period="1d", interval="1m")
                if df is not None and not df.empty:
                    last_row = df.iloc[-1]
                    last = float(last_row["Close"])
                    prev = float(df["Close"].iloc[-2]) if len(df) > 1 else last
                    data = {
                        "symbol": symbol, "last": last, 
                        "vol": int(last_row.get("Volume", 0)),
                        "pc": round((last - prev) / prev * 100, 3) if prev != 0 else 0.0,
                        "ts": datetime.now(timezone.utc).isoformat()
                    }
                    self.cache[symbol] = {"ts": self._now(), "data": data}
                    return data
            except Exception as e:
                logging.info("yfinance failed for %s: %s", symbol, e)
        return {"symbol": symbol, "last": 100.0, "vol": 0, "pc": 0.0}
    def get_stats(self, symbol):
        return self.fetch_latest(symbol)
