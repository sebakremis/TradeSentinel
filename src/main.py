# main.py

import streamlit as st
import pandas as pd

from src.storage import save_prices_incremental
from src.data_fetch import get_market_data
from src.dashboard_manager import intervals_full, intervals_main, load_all_prices
from src.tickers_store import load_followed_tickers
from src.config import BASE_DIR


def main():
    st.title("📊 TradeSentinel Dashboard")

    # Detect available intervals
    available_intervals = [p.name for p in BASE_DIR.iterdir() if p.is_dir()] if BASE_DIR.exists() else []

    if available_intervals:
        interval = st.selectbox("Select interval", available_intervals)
        df = load_all_prices(interval)

        if not df.empty:
            st.subheader(f"Market Data ({interval})")

            # --- START OF FIX ---
            # Define the columns you want to display on the dashboard
            display_columns = [
                'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume',
                'Ticker', 'Interval', 'Sector'
            ]
            
            # Create a new DataFrame with only the selected columns
            # This handles cases where some columns might be missing
            display_df = df.reindex(columns=display_columns)

            # Display the new DataFrame
            st.data_editor(display_df, num_rows="dynamic", height=500)
            # --- END OF FIX ---
        else:
            st.info(f"No data found for interval {interval}.")
    else:
        st.info("No market data found in database yet.")

    # Update button
    if st.button("Update Prices"):
        tickers = load_followed_tickers()
        if not tickers:
            st.warning("⚠️ No tickers found in followed_tickers_test.csv")
    
        for ticker in tickers:
            for period, interval in intervals_main.items():
                st.write(f"Fetching {ticker} with period={period}, interval={interval} …")
    
                # Fetch with period (Yahoo requirement)
                data = get_market_data(ticker, interval=interval, period=period)
    
                if not data.empty:
                    # Save under interval folder (e.g. data/prices/30m/, data/prices/1d/)
                    save_prices_incremental(ticker, interval, data)
                    st.success(f"✅ Saved {ticker} {interval} ({period})")
                else:
                    st.warning(f"⚠️ No data for {ticker} {period}/{interval}")
    
        st.rerun()

if __name__ == "__main__":
    main()









