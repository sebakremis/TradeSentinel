import streamlit as st
import pandas as pd

from src.storage import load_all_prices, save_prices_incremental, BASE_DIR
from src.data_fetch import get_market_data
from src.dashboard_manager import intervals_full, intervals_main
from src.tickers_store import load_followed_tickers


def main():
    st.title("📊 TradeSentinel Dashboard")

    # Detect available intervals
    available_intervals = [p.name for p in BASE_DIR.iterdir() if p.is_dir()] if BASE_DIR.exists() else []

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

    # Update button
    if st.button("Update Prices"):
        tickers = load_followed_tickers()
        if not tickers:
            st.warning("⚠️ No tickers found in followed_tickers_test.csv")
        for ticker in tickers:
            for period, interval in intervals_main.items():
                st.write(f"Fetching {ticker} {period}/{interval} …")
                data = get_market_data(ticker, interval=interval, period=period)
                if not data.empty:
                    save_prices_incremental(ticker, interval, data)
                    st.success(f"✅ Saved {ticker} {interval} ({period})")
                else:
                    st.warning(f"⚠️ No data for {ticker} {period}/{interval}")

        st.rerun()


if __name__ == "__main__":
    main()









