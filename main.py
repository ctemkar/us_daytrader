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
                    summary = f"Price:{stats['last']} Change:{stats.get('pc',0)} Vol:{stats.get('vol',0)}"
                    consensus = await llm.get_consensus(symbol, summary)
                    decision = consensus.get("decision", "HOLD")
                    conf = consensus.get("confidence", 0.0)
                    providers = consensus.get("providers", [])
                    votes = consensus.get("votes", [])
                    logging.info("RESULT %s -> %s (conf: %.3f) votes: %s details: %s", symbol, decision, conf, votes, providers)
                    if decision in ["BUY", "SELL"] and conf >= 0.7:
                        if risk.validate(symbol, decision, stats["last"]):
                            qty = int(INVESTMENT_CAP // stats["last"])
                            if qty > 0:
                                res = executor.place_order(symbol, decision, qty)
                                logging.info("Order Result: %s", res)
                except Exception as e:
                    logging.error("Loop error on %s: %s", symbol, e)
            logging.info("Sweep completed. Sleeping %s seconds", TICKER_INTERVAL)
            await asyncio.sleep(TICKER_INTERVAL)
    finally:
        await llm.close()

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("Stopped")
