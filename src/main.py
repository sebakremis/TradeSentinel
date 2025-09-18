import streamlit as st
import pandas as pd
from pathlib import Path

from src.tickers_store import load_followed_tickers
from src.data_fetch import get_market_data
from src.storage import save_prices_incremental, load_all_prices
from src.dashboard_manager import intervals_main

BASE_DIR = Path("data/prices")

load_all_prices()

def main():
    st.title("📊 TradeSentinel Dashboard")

    # 🔎 Detect available intervals dynamically
    if BASE_DIR.exists():
        available_intervals = [p.name for p in BASE_DIR.iterdir() if p.is_dir()]
    else:
        available_intervals = []

    if available_intervals:
        interval = st.selectbox("Select interval", available_intervals)
        df = load_all_prices(interval)

        if not df.empty:
            st.subheader(f"Market Data ({interval})")
            st.data_editor(df, num_rows="dynamic", height=500)
        else:
            st.info(f"No data found for interval {interval}.")
    else:
        st.info("No market data found in database yet.")

    # 🔄 Update button
    if st.button("Update Prices"):
        tickers = load_followed_tickers()
        for ticker in tickers:
            for period, interval in intervals_main.items():
                st.write(f"Fetching {ticker} {period} {interval}...")
                data = get_market_data(ticker, period, interval)
                if data is not None and not data.empty:
                    save_prices_incremental(ticker, interval, data)
        st.success("✅ Prices updated successfully!")
        st.rerun()  # modern replacement for experimental_rerun

if __name__ == "__main__":
    main()






