import os
import logging
from alpaca_trade_api.rest import REST
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

class OrderManager:
    def __init__(self):
        key_id = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_API_SECRET")
        
        if not key_id or not secret_key:
            raise ValueError("Missing Alpaca Credentials in .env")

        self.client = REST(
            key_id=key_id,
            secret_key=secret_key,
            base_url="https://paper-api.alpaca.markets"
        )
        self.allocation_per_trade = 25.0

    def place_order(self, symbol, side, price):
        try:
            order_side = "buy" if side.upper() == "BUY" else "sell"
            
            if order_side == "buy":
                qty = round(self.allocation_per_trade / price, 4)
            else:
                qty = int(self.allocation_per_trade // price)

            if qty <= 0:
                logging.info("Skipping %s: qty 0 for price %s (Alloc: $%s)", symbol, price, self.allocation_per_trade)
                return {"status": "skipped", "reason": "qty_zero"}

            order = self.client.submit_order(
                symbol=symbol,
                qty=qty,
                side=order_side,
                type="market",
                time_in_force="day"
            )
            return {"status": "success", "order_id": order.id, "qty": qty}

        except Exception as e:
            logging.error("Alpaca Order Error for %s: %s", symbol, e)
            return {"status": "error", "message": str(e)}
