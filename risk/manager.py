def calculate_position_size(equity, price, sl_price, risk_per_trade_pct):
    risk_amount = equity * (risk_per_trade_pct / 100)
    risk_per_share = abs(price - sl_price)
    if risk_per_share == 0: return 0
    return int(risk_amount / risk_per_share)
