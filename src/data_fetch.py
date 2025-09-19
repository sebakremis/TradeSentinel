import yfinance as yf
import pandas as pd
import streamlit as st
import time

def get_market_data(ticker, interval, period):
    """
    Fetches market data for a given ticker, interval, and period using yfinance.
    This version uses the yf.Ticker() object which is more stable than yf.download()
    for single tickers.

    Args:
        ticker (str): The stock ticker symbol.
        interval (str): The interval for the data (e.g., '30m', '1d').
        period (str): The period for the data (e.g., '1y', '5d').

    Returns:
        pd.DataFrame: A DataFrame with the fetched data, or an empty DataFrame on failure.
    """
    try:
        # Create a Ticker object for the given symbol
        stock_ticker = yf.Ticker(ticker)

        # Use the history method to get data. This method is often more reliable.
        data = stock_ticker.history(period=period, interval=interval, actions=False)

        # Check for empty or malformed data immediately
        if data.empty or data.dropna(how='all').empty or 'Close' not in data.columns:
            st.warning(f"⚠️ No data returned for {ticker} with interval {interval} and period {period}.")
            return pd.DataFrame()

        # Check if 'Close' column is a Series before converting to numeric
        if isinstance(data['Close'], pd.Series):
            data['Close'] = pd.to_numeric(data['Close'], errors='coerce')
        else:
            st.warning(f"⚠️ 'Close' column not found or is not a Series for {ticker}")
            return pd.DataFrame()

    except Exception as e:
        # Catch any exceptions during the API call or data processing
        st.error(f"❌ Error fetching data for {ticker}: {e}")
        return pd.DataFrame()

    # Add a small delay to avoid hitting API rate limits
    time.sleep(1)
    
    return data




