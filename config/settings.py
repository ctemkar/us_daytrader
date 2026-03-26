import os
from dotenv import load_dotenv

load_dotenv()
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_API_SECRET")
ALPACA_BASE_URL = "https://api.alpaca.markets"

TICKER_INTERVAL = "1Min"
INVESTMENT_CAP = 30.0
TAKE_PROFIT_PCT = 0.20
STOP_LOSS_PCT = 0.10
MIN_ORDER_SIZE = 25.0
MAX_POSITIONS = 10
TRADING_END_EST = "16:00"

SYMBOLS = [
    "NVDA", "MSFT", "TSLA", "AAPL", "AMD", "META", "SPY", "QQQ",
    "GOOGL", "AMZN", "NFLX", "INTC", "CSCO", "BA", "DIS", "V", "MA",
    "JPM", "BAC", "WMT", "KO", "PFE", "MRK", "XOM", "CVX", "T", "VZ",
    "UNH", "HD", "PG", "ABNB", "ORCL", "CRM", "ADBE", "AVGO", "COST"
]
