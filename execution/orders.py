import logging
from execution.alpaca_client import AlpacaClient
from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

class OrderManager:
    def __init__(self):
        self.client = AlpacaClient()

    def place_order(self, symbol, decision, price):
        allocation = float(settings.INVESTMENT_CAP) / float(settings.MAX_OPEN_POSITIONS)
        qty = int(allocation // price)
        
        if qty < 1:
            logging.info("Skipping %s: qty 0 for price %s (Alloc: $%s)", symbol, price, allocation)
            return {"status": "skipped"}

        side = "buy" if decision == "BUY" else "sell"
        
        try:
            res = self.client.create_order(symbol, qty, side)
            logging.info("Alpaca Order Result: %s", res)
            return res
        except Exception as e:
            logging.error("Alpaca Order Failed: %s", e)
            return {"status": "error", "message": str(e)}

    def get_position_qty(self, symbol):
        return self.client.get_position(symbol)
