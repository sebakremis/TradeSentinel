import pandas as pd
from pathlib import Path
import streamlit as st
from src.config import DATA_DIR
from src.data_fetch import get_multiple_market_data
from src.tickers_store import load_followed_tickers

@st.cache_data(ttl=3600)  # Cache the data for 1 hour (3600 seconds)
def get_all_prices_cached(tickers):
    """
    Fetches daily and intraday data for all tickers and combines them into two DataFrames.
    This function is decorated with Streamlit's caching to avoid re-fetching data on every rerun.
    It does NOT display any messages, as that is handled by the main app.
    """
    daily_data = get_multiple_market_data(tickers, interval='1d', period='1y')
    intraday_data = get_multiple_market_data(tickers, interval='30m', period='5d')

    if daily_data.empty or intraday_data.empty:
        # A simple warning can be useful for debugging a failure, but
        # info/success messages should be handled by the main app.
        st.warning("⚠️ Could not fetch data for all tickers.")
        return pd.DataFrame(), pd.DataFrame()

    all_daily_dfs = []
    all_intraday_dfs = []

    for ticker in tickers:
        if (ticker, 'Close') in daily_data.columns:
            df_daily = daily_data[ticker].copy()
            df_daily['Ticker'] = ticker
            all_daily_dfs.append(df_daily)

        if (ticker, 'Close') in intraday_data.columns:
            df_intraday = intraday_data[ticker].copy()
            df_intraday['Ticker'] = ticker
            all_intraday_dfs.append(df_intraday)

    df_daily_combined = pd.concat(all_daily_dfs).sort_index() if all_daily_dfs else pd.DataFrame()
    df_intraday_combined = pd.concat(all_intraday_dfs).sort_index() if all_intraday_dfs else pd.DataFrame()

    return df_daily_combined, df_intraday_combined

def load_all_prices(interval):
    """
    This function now acts as a wrapper, retrieving the cached DataFrame.
    """
    tickers_df = load_followed_tickers()
    if tickers_df.empty:
        return pd.DataFrame()
    
    tickers = tickers_df['Ticker'].tolist()
    
    df_daily, df_intraday = get_all_prices_cached(tickers)
    
    if interval == '1d':
        return df_daily
    elif interval == '30m':
        return df_intraday
    return pd.DataFrame()              










