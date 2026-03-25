import os
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

try:
    from llm.client import LLMClient
except Exception as e:
    logging.error("LLM client import failed %s", e)
    raise

INVESTMENT_CAP = float(os.getenv("INVESTMENT_CAP", "250"))
LIVE_ORDERS = os.getenv("LIVE_ORDERS", "False").lower() in ("1", "true", "yes")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "15"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "8"))
SYMBOL_TIMEOUT = float(os.getenv("SYMBOL_TIMEOUT", "12"))

try:
    from config.settings import SYMBOLS as CFG_SYMBOLS
    SYMBOLS = CFG_SYMBOLS
except Exception:
    SYMBOLS = ["AAPL", "MSFT", "NVDA"]

async def fetch_data_summary(symbol):
    try:
        from data.processor import get_intraday_summary
        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(None, lambda: get_intraday_summary(symbol))
        return summary or "no data"
    except Exception as e:
        logging.warning("fetch_data_summary failed for %s %s", symbol, e)
        return "no data"

def compute_qty_from_cap(price):
    try:
        price = float(price)
        if price <= 0:
            return 0
        qty = int(max(1, INVESTMENT_CAP // price))
        return qty
    except Exception:
        return 0

def check_risk(symbol, decision, confidence):
    try:
        from risk.guard import is_safe_to_trade
        return is_safe_to_trade(symbol, decision, confidence)
    except Exception:
        if decision in ("HOLD",):
            return False
        return confidence >= 0.6

def execute_trade(symbol, decision, qty, price):
    side = None
    short_flag = False
    if decision == "BUY":
        side = "buy"
    elif decision == "SELL":
        side = "sell"
    elif decision == "SHORT":
        side = "sell"
        short_flag = True
    elif decision == "COVER":
        side = "buy"
    else:
        logging.info("No execution for %s decision %s", symbol, decision)
        return {"status": "skipped", "reason": "HOLD or unknown decision"}
    try:
        from execution.orders import place_order
        resp = place_order(symbol=symbol, side=side, qty=qty, price=price, dry_run=not LIVE_ORDERS, short=short_flag)
        return {"status": "placed", "resp": resp}
    except Exception as e:
        logging.warning("place_order not available falling back to schwab_ops %s", e)
        try:
            from execution.schwab_ops import create_order
            resp = create_order(symbol=symbol, side=side, qty=qty, limit_price=price, dry_run=not LIVE_ORDERS, short=short_flag)
            return {"status": "placed_schwab_ops", "resp": resp}
        except Exception as e2:
            logging.error("No execution module available %s %s", e, e2)
            return {"status": "failed", "error": str(e2)}

async def handle_symbol(llm, symbol, sem):
    await sem.acquire()
    try:
        summary = await fetch_data_summary(symbol)
        try:
            consensus = await asyncio.wait_for(llm.get_consensus(symbol, summary), timeout=SYMBOL_TIMEOUT)
        except asyncio.TimeoutError:
            logging.warning("LLM timeout for %s", symbol)
            return {"symbol": symbol, "status": "llm_timeout"}
        except Exception as e:
            logging.error("LLM error for %s %s", symbol, e)
            return {"symbol": symbol, "status": "llm_error", "error": str(e)}
        
        decision = consensus.get("decision", "HOLD")
        confidence = float(consensus.get("confidence", 0.0))
        votes = consensus.get("votes", [0, 0, 0, 0, 0])
        providers = consensus.get("providers", [])
        
        prov_details = []
        for p in providers:
            p_name = p.get("provider", "??")
            p_dec = p.get("decision", "HOLD")
            p_conf = p.get("confidence", 0.0)
            prov_details.append(f"{p_name}:{p_dec}({p_conf})")
        
        details_str = " | ".join(prov_details)
        logging.info("RESULT %s -> %s (conf: %.3f) votes: %s details: [%s]", 
                     symbol, decision, confidence, votes, details_str)

        if decision in ("BUY", "SELL", "SHORT", "COVER"):
            try:
                from data.processor import get_latest_price
                price = get_latest_price(symbol)
            except Exception:
                try:
                    price = float(os.getenv("ASSUME_PRICE", "100"))
                except Exception:
                    price = 100.0
            qty = compute_qty_from_cap(price)
            if qty <= 0:
                logging.info("Computed qty 0 for %s price %s", symbol, price)
                return {"symbol": symbol, "status": "zero_qty"}
            allowed = check_risk(symbol, decision, confidence)
            if not allowed:
                logging.info("Risk guard blocked %s %s %s", symbol, decision, confidence)
                return {"symbol": symbol, "status": "risk_blocked"}
            result = execute_trade(symbol, decision, qty, price)
            logging.info("Execution result %s", result)
            return {"symbol": symbol, "status": "executed", "result": result}
        else:
            return {"symbol": symbol, "status": "hold"}
    finally:
        sem.release()

async def main_loop():
    llm = LLMClient()
    sem = asyncio.Semaphore(CONCURRENCY)
    try:
        while True:
            logging.info("Starting sweep for %d symbols", len(SYMBOLS))
            tasks = [asyncio.create_task(handle_symbol(llm, s, sem)) for s in SYMBOLS]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            processed = 0
            for r in results:
                if isinstance(r, Exception):
                    logging.error("symbol task raised exception %s", r)
                else:
                    processed += 1
            logging.info("Sweep completed processed %d/%d", processed, len(SYMBOLS))
            await asyncio.sleep(POLL_INTERVAL)
    finally:
        await llm.close()

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("Shutting down")
