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
            # Create a copy to avoid modifying the original DataFrame
            display_df = df.copy()
            
            # Reset the index to make 'Date' a column, preventing KeyError
            if display_df.index.name is not None:
                display_df = display_df.reset_index(names=[display_df.index.name])
            else:
                display_df = display_df.reset_index(names=['Date'])
            
            # Sort by Ticker and Date to ensure the last entry is the most recent
            display_df = display_df.sort_values(['Ticker', 'Date'])
            
            # Calculate 'Change' and 'Change %'
            # Group by ticker to perform calculations within each stock's data
            display_df['Change'] = display_df.groupby('Ticker')['Close'].diff()
            display_df['Change %'] = display_df.groupby('Ticker')['Close'].pct_change() * 100
            
            # Get the last price for each unique ticker
            last_prices_df = display_df.groupby('Ticker').tail(1)
            
            # Define the columns to display
            display_columns = ['Ticker', 'Close', 'Change', 'Change %', 'Date']
            
            # Display the final DataFrame in Streamlit
            st.dataframe(last_prices_df[display_columns], hide_index=True)
                    
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









