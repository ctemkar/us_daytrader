import pandas as pd
import numpy as np

class DataProcessor:
    def __init__(self):
        pass

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Simple Moving Average 20
        df['sma20'] = df['close'].rolling(window=20).mean()
        # Exponential Moving Average 50
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        # Relative Strength Index (RSI) 14
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi14'] = 100 - (100 / (1 + rs))
        # Bollinger Bands 20, 2 std
        df['bb_mid'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
        return df

    def get_summary(self, df: pd.DataFrame) -> str:
        latest = df.iloc[-1]
        summary = (
            f"SMA20: {latest['sma20']:.2f}, "
            f"EMA50: {latest['ema50']:.2f}, "
            f"RSI14: {latest['rsi14']:.2f}, "
            f"BB Upper: {latest['bb_upper']:.2f}, "
            f"BB Lower: {latest['bb_lower']:.2f}, "
            f"Close: {latest['close']:.2f}"
        )
        return summary
