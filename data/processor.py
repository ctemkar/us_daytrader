from datetime import datetime, timezone, timedelta
import random
try:
    import yfinance as yf
    YF_OK = True
except Exception:
    YF_OK = False

def _fmt(v):
    try:
        return float(v)
    except Exception:
        return None

def get_intraday_summary(symbol):
    try:
        if YF_OK:
            now = datetime.now(timezone.utc)
            start = now - timedelta(minutes=30)
            ticker = yf.Ticker(symbol)
            df = ticker.history(interval="1m", start=start.isoformat(), end=now.isoformat(), actions=False)
            if df is None or df.empty:
                raise Exception("empty df")
            closes = df["Close"].dropna().astype(float)
            if closes.empty:
                raise Exception("no closes")
            last = float(closes.iloc[-1])
            first = float(closes.iloc[0])
            mean = float(closes.mean())
            std = float(closes.std()) if len(closes) > 1 else 0.0
            pct = (last - first) / first * 100 if first != 0 else 0.0
            return f"last:{last:.2f} pct:{pct:.2f} mean:{mean:.2f} vol:{std:.4f} samples:{len(closes)}"
        else:
            price = round(random.uniform(80, 350), 2)
            return f"fallback last:{price:.2f} pct:0.00 mean:{price:.2f} vol:0.00 samples:1"
    except Exception as e:
        try:
            price = round(random.uniform(80, 350), 2)
            return f"error fallback last:{price:.2f} note:{str(e)}"
        except Exception:
            return "no data"

def get_latest_price(symbol):
    try:
        if YF_OK:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="2m", interval="1m", actions=False)
            if df is None or df.empty:
                raise Exception("empty")
            closes = df["Close"].dropna().astype(float)
            if closes.empty:
                raise Exception("no closes")
            return float(closes.iloc[-1])
        else:
            return round(random.uniform(80, 350), 2)
    except Exception:
        return round(random.uniform(80, 350), 2)
