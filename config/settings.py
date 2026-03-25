import os
from pathlib import Path

def load_env():
    p = Path(".env")
    if not p.exists(): return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or "=" not in line: continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"')

load_env()

SYMBOLS = [
  "NVDA","MSFT","TSLA","AAPL","AMD","META","SPY","QQQ","GOOGL","AMZN",
  "NFLX","INTC","CSCO","BA","DIS","V","MA","JPM","BAC","WMT",
  "KO","PFE","MRK","XOM","CVX","T","VZ","UNH","HD","PG",
  "ABNB","ORCL","CRM","ADBE","AVGO","COST"
]
INVESTMENT_CAP = 250
POLL_INTERVAL = 15
TICKER_INTERVAL = POLL_INTERVAL
LIVE_ORDERS = True
ENABLE_SHORTS = True
MIN_ORDER_USD = 1
MAX_OPEN_POSITIONS = 10
ORDER_TYPE = "market"
ORDER_TIF = "day"

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://api.alpaca.markets")
