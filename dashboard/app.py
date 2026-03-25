from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import json
import os
import time

STATE_FILE = os.getenv('ENGINE_STATE_FILE', 'engine_state.json')
REFRESH_SECONDS = int(os.getenv('DASH_REFRESH_SEC', '3'))

st.set_page_config(page_title="Daytrader Dashboard", layout="wide")

st.markdown('<meta http-equiv="refresh" content="{}">'.format(REFRESH_SECONDS), unsafe_allow_html=True)

st.title("Daytrader Live Dashboard")

col1, col2 = st.columns([3,1])

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

state = load_state()

if not state or "symbols" not in state:
    st.warning("No engine state found yet. Run the trading engine first")
    if st.button("Refresh now"):
        st.experimental_rerun()
    st.stop()

with col1:
    st.header("Symbols")
    rows = []
    for sym, info in state.get("symbols", {}).items():
        rows.append({
            "symbol": sym,
            "decision": info.get("decision"),
            "confidence": info.get("confidence"),
            "price": info.get("price"),
            "time_utc": info.get("time_utc")
        })
    st.dataframe(rows)

with col2:
    st.header("Status")
    st.write("Last update")
    st.write(state.get("last_update", "n/a"))
    if st.button("Refresh now"):
        st.experimental_rerun()

st.header("Detailed breakdown per symbol")
for sym, info in state.get("symbols", {}).items():
    with st.expander(sym + "  " + str(info.get("decision")) + "  conf " + str(info.get("confidence"))):
        st.write("price", info.get("price"))
        st.write("time", info.get("time_utc"))
        st.subheader("LLM breakdown")
        for b in info.get("breakdown", []):
            st.write(b)
        st.markdown("---")
