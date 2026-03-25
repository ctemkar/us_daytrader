import os
import requests
import time

class AlpacaClient:
    def __init__(self, paper=True):
        self.paper = paper
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.api_secret = os.getenv('ALPACA_API_SECRET')
        self.trading_base = 'https://paper-api.alpaca.markets' if paper else 'https://api.alpaca.markets'
        self.data_base = 'https://data.alpaca.markets'
        self.headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.api_secret
        }

    def get_historical(self, symbol, timeframe='1Min', limit=100):
        symbol = symbol.upper()
        url = f"{self.data_base}/v2/stocks/{symbol}/bars"
        params = {
            'timeframe': timeframe,
            'limit': limit
        }
        r = requests.get(url, headers=self.headers, params=params, timeout=10)
        if r.status_code != 200:
            print(f"Error fetching historical data for {symbol}: {r.status_code} {r.text}")
            return None
        data = r.json()
        bars = data.get('bars', [])
        if not bars:
            print(f"No bars returned for {symbol}")
            return None
        import pandas as pd
        df = pd.DataFrame(bars)
        if 't' in df.columns:
            df['t'] = pd.to_datetime(df['t'])
            df.rename(columns={'t': 'datetime', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
            df.set_index('datetime', inplace=True)
            return df
        else:
            print(f"Unexpected data format for {symbol}: {data}")
            return None

    def create_market_order(self, symbol, side, qty):
        url = f"{self.trading_base}/v2/orders"
        data = {
            "symbol": symbol,
            "qty": qty,
            "side": side.lower(),
            "type": "market",
            "time_in_force": "day"
        }
        r = requests.post(url, headers=self.headers, json=data, timeout=10)
        if r.status_code not in (200, 201):
            print(f"Order error for {symbol}: {r.status_code} {r.text}")
            return False
        try:
            j = r.json()
            print(f"Order placed: {side} {qty} {symbol} id {j.get('id')}")
        except Exception:
            print(f"Order placed: {side} {qty} {symbol} but failed to parse response")
        return True
