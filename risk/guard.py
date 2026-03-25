import logging
from execution.orders import OrderManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

class RiskGuard:
    def __init__(self):
        self.executor = OrderManager()

    def validate(self, symbol, decision, price):
        if decision == "BUY":
            return self._check_buy_rules(symbol, price)
        elif decision == "SELL":
            return self._check_sell_rules(symbol, price)
        return True

    def _check_buy_rules(self, symbol, price):
        pos = self.executor.get_position_qty(symbol)
        if pos > 0:
            avg_entry = self._get_avg_entry_price(symbol)
            if avg_entry and price:
                pnl = (price - avg_entry) / avg_entry
                if pnl >= 0.20:
                    logging.info("TAKE PROFIT: %s at +%.1f%%", symbol, pnl * 100)
                    self.executor.place_order(symbol, "SELL", price)
                    return False
                elif pnl <= -0.10:
                    logging.info("STOP LOSS: %s at %.1f%%", symbol, pnl * 100)
                    self.executor.place_order(symbol, "SELL", price)
                    return False
        return True

    def _check_sell_rules(self, symbol, price):
        pos = self.executor.get_position_qty(symbol)
        if pos > 0:
            avg_entry = self._get_avg_entry_price(symbol)
            if avg_entry and price:
                pnl = (price - avg_entry) / avg_entry
                if pnl >= 0.20 or pnl <= -0.10:
                    logging.info("EXIT SIGNAL: %s at %.1f%% PnL", symbol, pnl * 100)
                    return True
        return True

    def _get_avg_entry_price(self, symbol):
        try:
            import requests
            from config import settings
            url = f"{settings.ALPACA_BASE_URL}/v2/positions/{symbol}"
            headers = {
                "APCA-API-KEY-ID": settings.ALPACA_API_KEY,
                "APCA-API-SECRET-KEY": settings.ALPACA_SECRET_KEY
            }
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                return float(resp.json().get("avg_entry_price", 0))
        except Exception:
            pass
        return 0
