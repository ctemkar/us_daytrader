import pandas as pd
import numpy as np

class DataProcessor:
    def calculate_indicators(self, df):
        if len(df) < 20: return df
        df = df.copy()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        return df

    def get_summary(self, df):
        if df.empty: return "No data"
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        change = ((last['close'] - prev['close']) / prev['close']) * 100
        
        rsi_val = f"{last['rsi']:.2f}" if 'rsi' in last and not np.isnan(last['rsi']) else "N/A"
        macd_val = f"{last['macd']:.2f}" if 'macd' in last and not np.isnan(last['macd']) else "N/A"
        
        return f"Price: {last['close']:.2f}, Change: {change:.3f}%, RSI: {rsi_val}, MACD: {macd_val}"
