def generate_signal(symbol, df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    bullish = last['close'] > last['vwap'] and last['close'] > last['ema9'] and prev['close'] < prev['ema9']
    bearish = last['close'] < last['vwap'] and last['close'] < last['ema9'] and prev['close'] > prev['ema9']
    if bullish: return "LONG", 8.5
    if bearish: return "SHORT", 8.2
    return "WAIT", 0
