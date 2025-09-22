import pandas as pd
import yfinance as yf
import streamlit as st
import datetime as dt
from src.storage import save_prices_incremental
from src.tickers_store import load_followed_tickers

def get_multiple_market_data(tickers, interval, period):
    """
    Fetches market data for multiple tickers from Yahoo Finance.
    
    Returns:
        pd.DataFrame: A DataFrame with a MultiIndex column structure or an empty DataFrame.
    """
    try:
        data = yf.download(
            tickers=tickers,
            period=period,
            interval=interval,
            group_by='ticker',
            auto_adjust=True,
            threads=True,
            proxy=None
        )
        return data
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def fetch_and_save_data(tickers: list) -> bool:
    """
    Fetches market data for a list of tickers and saves it incrementally.
    Returns True if data was successfully saved for at least one ticker, False otherwise.
    """
    st.info("Fetching all tickers at once. This may take a moment...")
    
    saved_files_count = 0
    try:
        daily_data = get_multiple_market_data(tickers=tickers, interval='1d', period='1y')
        intraday_data = get_multiple_market_data(tickers=tickers, interval='30m', period='5d')

        if not daily_data.empty:
            for ticker in tickers:
                if (ticker, 'Close') in daily_data.columns:
                    save_prices_incremental(ticker, '1d', daily_data[ticker])
                    saved_files_count += 1
                else:
                    st.warning(f"⚠️ No daily data found for {ticker}")
        
        if not intraday_data.empty:
            for ticker in tickers:
                if (ticker, 'Close') in intraday_data.columns:
                    save_prices_incremental(ticker, '30m', intraday_data[ticker])
                    saved_files_count += 1
                else:
                    st.warning(f"⚠️ No intraday data found for {ticker}")
        
        return saved_files_count > 0
    
    except Exception as e:
        st.error(f"❌ An error occurred during data fetching: {e}")
        return False


