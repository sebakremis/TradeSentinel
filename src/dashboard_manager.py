import pandas as pd
from pathlib import Path
import streamlit as st
from src.config import DATA_DIR
from src.data_manager import get_multiple_market_data
from src.tickers_manager import load_followed_tickers

@st.cache_data(ttl=3600)  # Cache the data for 1 hour (3600 seconds)
def get_all_prices_cached(tickers):
    """
    Fetches daily and intraday data for all tickers and combines them into two DataFrames.
    This function is decorated with Streamlit's caching to avoid re-fetching data on every rerun.
    It does NOT display any messages, as that is handled by the main app.
    """
    daily_data = get_multiple_market_data(tickers, interval='1d', period='1y')
    

    if daily_data.empty:
        # A simple warning can be useful for debugging a failure, but
        # info/success messages should be handled by the main app.
        st.warning("⚠️ Could not fetch data for all tickers.")
        return pd.DataFrame(), pd.DataFrame()

    all_daily_dfs = []
    

    for ticker in tickers:
        if (ticker, 'Close') in daily_data.columns:
            df_daily = daily_data[ticker].copy()
            df_daily['Ticker'] = ticker
            all_daily_dfs.append(df_daily)

        

    df_daily_combined = pd.concat(all_daily_dfs).sort_index() if all_daily_dfs else pd.DataFrame()
    

    return df_daily_combined

def load_all_prices():
    """
    This function now acts as a wrapper, retrieving the cached DataFrame.
    """
    tickers_df = load_followed_tickers()
    if tickers_df.empty:
        return pd.DataFrame()
    
    tickers = tickers_df['Ticker'].tolist()
    
    df_daily = get_all_prices_cached(tickers)
    
    return df_daily             










