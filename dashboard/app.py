import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

import streamlit as st
import pandas as pd
import time
from data.processor import DataProcessor

st.set_page_config(page_title="AI Day Trader", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp { background-color: #0e1117; color: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 AI Day Trader - Live Dashboard")

processor = DataProcessor()
symbols = ["NVDA", "MSFT", "TSLA", "AAPL", "AMD", "META", "SPY", "QQQ", "GOOGL", "AMZN"]

placeholder = st.empty()

while True:
    with placeholder.container():
        cols = st.columns(4)
        for i, symbol in enumerate(symbols[:4]):
            stats = processor.get_stats(symbol)
            price = stats.get("last", "N/A")
            pc = stats.get("pc", 0.0)
            delta_str = f"{pc:+.2f}%"
            cols[i].metric(symbol, f"${price:.2f}", delta=delta_str)

        st.divider()
        
        data = []
        for symbol in symbols:
            stats = processor.get_stats(symbol)
            data.append({
                "Symbol": symbol,
                "Price": f"${stats.get('last', 'N/A'):.2f}",
                "Change %": f"{stats.get('pc', 0.0):+.2f}%",
                "Volume": stats.get("vol", 0),
                "Timestamp": stats.get("ts", "")
            })
        
        df = pd.DataFrame(data)
        st.table(df)
        
        st.caption(f"Last Update: {time.strftime('%H:%M:%S')} ICT")
    
    time.sleep(10)
