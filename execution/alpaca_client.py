import requests
import logging
from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

class AlpacaClient:
    def __init__(self):
        self.key = settings.ALPACA_API_KEY
        self.secret = settings.ALPACA_SECRET_KEY
        self.base_url = settings.ALPACA_BASE_URL
        self.headers = {
            "APCA-API-KEY-ID": self.key,
            "APCA-API-SECRET-KEY": self.secret,
            "Content-Type": "application/json"
        }

    def create_order(self, symbol, qty, side, order_type="market", time_in_force="day"):
        url = f"{self.base_url}/v2/orders"
        data = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force
        }
        resp = requests.post(url, json=data, headers=self.headers)
        return resp.json()

    def get_position(self, symbol):
        url = f"{self.base_url}/v2/positions/{symbol}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 404: return 0
        return float(resp.json().get("qty", 0))
