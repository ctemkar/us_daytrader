def create_bracket_order(symbol, quantity, entry_price, sl_price, tp_price):
    order = {
        "orderType": "LIMIT",
        "session": "NORMAL",
        "duration": "DAY",
        "orderStrategyType": "TRIGGER",
        "orderLegCollection": [{
            "instruction": "BUY",
            "quantity": quantity,
            "symbol": symbol,
            "price": entry_price
        }],
        "childOrderStrategies": [
            {"orderType": "STOP", "instruction": "SELL", "quantity": quantity, "stopPrice": sl_price},
            {"orderType": "LIMIT", "instruction": "SELL", "quantity": quantity, "price": tp_price}
        ]
    }
    return order
