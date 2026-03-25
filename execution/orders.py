import os
import logging

def place_order(symbol, side, qty, price=None, dry_run=True, short=False):
    try:
        from execution.alpaca_engine import create_alpaca_order
        
        asset_class = "us_equity"
        if symbol.upper().endswith("USD") or symbol.upper().endswith("BTC") or symbol.upper().endswith("ETH"):
            asset_class = "crypto"
            
        return create_alpaca_order(
            symbol=symbol, 
            side=side, 
            qty=qty, 
            limit_price=price, 
            dry_run=dry_run, 
            short=short,
            asset_class=asset_class
        )
    except Exception as e:
        logging.error("Order routing failed: %s", e)
        return {"status": "failed", "error": str(e)}
