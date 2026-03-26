import asyncio
import logging
from datetime import datetime, time
import pytz
import alpaca_trade_api as tradeapi
from config.settings import (
    SYMBOLS, TICKER_INTERVAL, INVESTMENT_CAP,
    ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL,
    TRADING_END_EST, TAKE_PROFIT_PCT, STOP_LOSS_PCT
)
from data.processor import DataProcessor
from llm.client import LLMClient
from risk.guard import RiskGuard

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
EST = pytz.timezone('US/Eastern')

async def run_engine():
    api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL, api_version='v2')
    processor = DataProcessor()
    llm = LLMClient()
    risk = RiskGuard()

    logging.info(f"=== ENGINE START: LIVE MODE ({ALPACA_BASE_URL}) ===")

    while True:
        now_est = datetime.now(EST).time()
        cutoff = time.fromisoformat(TRADING_END_EST)

        if now_est >= cutoff:
            logging.info("Market closed. Closing all positions.")
            for p in api.list_positions():
                try:
                    api.submit_order(
                        symbol=p.symbol,
                        qty=abs(float(p.qty)),
                        side="sell" if float(p.qty) > 0 else "buy",
                        type="market",
                        time_in_force="day"
                    )
                except Exception as e:
                    logging.error(f"Error closing {p.symbol}: {e}")
            await asyncio.sleep(3600)
            continue

        positions = {p.symbol: float(p.qty) for p in api.list_positions()}
        account = api.get_account()
        buying_power = float(account.buying_power)

        for symbol in SYMBOLS:
            try:
                logging.info(f"--- {symbol} ---")
                bars = api.get_bars(symbol, TICKER_INTERVAL, limit=50).df
                if bars.empty:
                    logging.info(f"No data for {symbol}, skipping.")
                    continue

                bars.columns = [c.lower() for c in bars.columns]
                df = processor.calculate_indicators(bars)
                summary = processor.get_summary(df)

                decision = await llm.get_consensus(symbol, summary)
                logging.info(f"Decision: {decision['decision']} (conf: {decision['confidence']})")

                qty = positions.get(symbol, 0.0)
                last_price = df['close'].iloc[-1]

                if qty != 0:
                    pos_detail = api.get_position(symbol)
                    avg_price = float(pos_detail.avg_entry_price)
                    gain = (last_price - avg_price) / avg_price if qty > 0 else (avg_price - last_price) / avg_price
                    if gain >= TAKE_PROFIT_PCT or gain <= -STOP_LOSS_PCT:
                        logging.info(f"EXIT {symbol} at {gain:.2%}")
                        api.submit_order(
                            symbol=symbol,
                            qty=abs(qty),
                            side="sell" if qty > 0 else "buy",
                            type="market",
                            time_in_force="day"
                        )
                elif risk.can_enter_new_position(len(positions)):
                    if decision['decision'] in ["BUY", "SELL"]:
                        side = "buy" if decision['decision'] == "BUY" else "sell"
                        max_qty_by_cap = INVESTMENT_CAP / last_price
                        max_qty_by_power = buying_power / last_price if side == "buy" else max_qty_by_cap  # Simplified for shorts
                        order_qty = round(min(max_qty_by_cap, max_qty_by_power), 4)

                        if order_qty >= 0.01:
                            logging.info(f"LIVE EXECUTE: {side.upper()} {symbol} qty {order_qty}")
                            api.submit_order(
                                symbol=symbol,
                                qty=order_qty,
                                side=side,
                                type="market",
                                time_in_force="day"
                            )
                        else:
                            logging.info(f"Not enough buying power to {side} {symbol}")
                else:
                    logging.info(f"Skipping {symbol}: Active position {qty}")

            except Exception as e:
                logging.error(f"Error {symbol}: {e}")

            await asyncio.sleep(0.5)

        logging.info("Sweep complete. Waiting 60s...")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(run_engine())
