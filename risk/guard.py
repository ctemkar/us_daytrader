import config.settings as s

def validate_trade(current_equity, daily_pnl, active_count):
    if daily_pnl <= -(s.INVESTMENT_CAP * (s.MAX_DAILY_LOSS_PCT / 100)):
        return False, "Daily Loss Limit Hit"
    if active_count >= s.MAX_POSITIONS:
        return False, "Max Positions Reached"
    return True, "Risk Check Passed"

def get_position_size(price, sl_pct):
    risk_amt = s.INVESTMENT_CAP * (s.RISK_PER_TRADE_PCT / 100)
    risk_per_share = price * (sl_pct / 100)
    if risk_per_share <= 0: return 0
    size = int(risk_amt / risk_per_share)
    max_size = int(s.INVESTMENT_CAP / price)
    return min(size, max_size)
