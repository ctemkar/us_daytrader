import os
import logging
from execution.paper_ops import PaperClient
from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

INVESTMENT_CAP = settings.INVESTMENT_CAP
LIVE_ORDERS = settings.LIVE_ORDERS
ENABLE_SHORTS = settings.ENABLE_SHORTS
MIN_ORDER_USD = settings.MIN_ORDER_USD
MAX_OPEN_POSITIONS = settings.MAX_OPEN_POSITIONS

class OrderManager:
    def __init__(self):
        self.client = PaperClient()
    def compute_qty(self, price, allocation_usd):
        try:
            if price is None or price <= 0:
                return 0
            qty = int(allocation_usd // price)
            return max(qty, 0)
        except Exception:
            return 0
    def place_order(self, symbol, decision, price, allocation_usd=None):
        allocation = allocation_usd if allocation_usd is not None else (INVESTMENT_CAP / MAX_OPEN_POSITIONS)
        qty = self.compute_qty(price, allocation)
        if qty < 1 or allocation < MIN_ORDER_USD:
            logging.info("Order skipped qty<1 or allocation<min for %s qty %s alloc %s", symbol, qty, allocation)
            return {"status": "skipped", "reason": "qty_zero_or_allocation_small", "qty": qty}
        if decision == "BUY":
            return self._buy(symbol, qty)
        if decision == "SELL":
            return self._sell_or_short(symbol, qty)
        logging.info("No action for decision %s on %s", decision, symbol)
        return {"status": "no_action"}
    def _buy(self, symbol, qty):
        if not LIVE_ORDERS:
            logging.info("DRY RUN: BUY %s %s", qty, symbol)
            return {"status": "dry_run", "side": "buy", "symbol": symbol, "qty": qty}
        try:
            res = self.client.create_order(symbol=symbol, qty=qty, side="buy", order_type=settings.ORDER_TYPE, time_in_force=settings.ORDER_TIF, short=False)
            logging.info("Order Result: %s", res)
            return res
        except Exception as e:
            logging.error("Buy failed %s %s", symbol, e)
            return {"status": "error", "error": str(e)}
    def _sell_or_short(self, symbol, qty):
        try:
            position = int(self.client.get_position_qty(symbol) or 0)
        except Exception:
            position = 0
        if position >= qty and position > 0:
            return self._sell_existing(symbol, qty)
        if position > 0 and qty > position:
            sell_qty = position
            return self._sell_existing(symbol, sell_qty)
        if position == 0:
            if not ENABLE_SHORTS:
                logging.info("No shares to sell and shorts disabled for %s", symbol)
                return {"status": "skipped", "reason": "no_shares_and_shorts_disabled"}
            return self._short_open(symbol, qty)
        return {"status": "skipped", "reason": "insufficient_position"}
    def _sell_existing(self, symbol, qty):
        if not LIVE_ORDERS:
            logging.info("DRY RUN: SELL %s %s", qty, symbol)
            return {"status": "dry_run", "side": "sell", "symbol": symbol, "qty": qty}
        try:
            res = self.client.create_order(symbol=symbol, qty=qty, side="sell", order_type=settings.ORDER_TYPE, time_in_force=settings.ORDER_TIF, short=False)
            logging.info("Order Result: %s", res)
            return res
        except Exception as e:
            logging.error("Sell failed %s %s", symbol, e)
            return {"status": "error", "error": str(e)}
    def _short_open(self, symbol, qty):
        if not LIVE_ORDERS:
            logging.info("DRY RUN: SHORT %s %s", qty, symbol)
            return {"status": "dry_run", "side": "short", "symbol": symbol, "qty": qty}
        if not ENABLE_SHORTS:
            return {"status": "skipped", "reason": "shorts_disabled"}
        try:
            res = self.client.create_order(symbol=symbol, qty=qty, side="sell", order_type=settings.ORDER_TYPE, time_in_force=settings.ORDER_TIF, short=True)
            logging.info("Short Order Result: %s", res)
            return res
        except Exception as e:
            logging.error("Short failed %s %s", symbol, e)
            return {"status": "error", "error": str(e)}
    def get_position_qty(self, symbol):
        try:
            return int(self.client.get_position_qty(symbol) or 0)
        except Exception:
            return 0
    def get_positions(self):
        try:
            return self.client.get_positions()
        except Exception:
            return {}
    def close_all(self):
        return self.client.close_all()
