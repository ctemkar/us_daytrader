import pandas as pd
import numpy as np

def calculate_vwap(df):
    tp = (df['high'] + df['low'] + df['close']) / 3
    return (tp * df['volume']).cumsum() / df['volume'].cumsum()

def get_opening_range(df, minutes=15):
    opening_data = df.head(minutes)
    return opening_data['high'].max(), opening_data['low'].min()
