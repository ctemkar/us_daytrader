#!/bin/zsh

cat << 'EOC' > risk/guard.py
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
EOC

cat << 'EOM' > main.py
import os
import asyncio
import logging
from config.settings import SYMBOLS, TICKER_INTERVAL, INVESTMENT_CAP
from data.processor import DataProcessor
from signals.engine import SignalEngine
from llm.client import LLMClient
from execution.orders import OrderManager
from risk.guard import RiskGuard

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

async def main_loop():
    data_proc = DataProcessor()
    sig_engine = SignalEngine()
    llm = LLMClient()
    executor = OrderManager()
    risk = RiskGuard()
    logging.info("Starting Alpaca Day Trader - Cap: $%s", INVESTMENT_CAP)
    try:
        while True:
            logging.info("Starting sweep for %s symbols", len(SYMBOLS))
            for symbol in SYMBOLS:
                try:
                    stats = data_proc.get_stats(symbol)
                    if not stats or stats.get("last", 0) <= 0:
                        continue
                    price = float(stats["last"])
                    summary = f"Price:{price} Change:{stats.get('pc',0)} Vol:{stats.get('vol',0)}"
                    consensus = await llm.get_consensus(symbol, summary)
                    decision = consensus.get("decision", "HOLD")
                    conf = consensus.get("confidence", 0.0)
                    providers = consensus.get("providers", [])
                    votes = consensus.get("votes", [])
                    logging.info("RESULT %s -> %s (conf: %.3f) votes: %s details: %s", symbol, decision, conf, votes, providers)
                    if decision in ["BUY", "SELL"] and conf >= 0.7:
                        if risk.validate(symbol, decision, price):
                            res = executor.place_order(symbol, decision, price)
                            logging.info("Order Result: %s", res)
                except Exception as e:
                    logging.error("Loop error on %s: %s", symbol, e)
            await asyncio.sleep(TICKER_INTERVAL)
    finally:
        await llm.close()

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("Stopped")
EOM

echo "Quant protection setup done. Run 'python3 main.py' to start trading with profit/loss exit rules."
