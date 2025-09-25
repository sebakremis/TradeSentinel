# src/dashboard_manager.py
import pandas as pd
import streamlit as st
from src.data_manager import get_multiple_market_data
from src.tickers_manager import load_followed_tickers
from src.database_manager import init_db, save_prices_to_db, load_prices_from_db

# Initialize the database on application startup
init_db()

def fetch_and_store_prices(tickers):
    """
    Fetches data from the external API, stores it in the database, 
    and returns a combined DataFrame.
    """
    daily_data = get_multiple_market_data(tickers, interval='1d', period='1y')
    
    if daily_data.empty:
        st.warning("⚠️ Could not fetch data for all tickers.")
        return pd.DataFrame()

    all_daily_dfs = []
    for ticker in tickers:
        if (ticker, 'Close') in daily_data.columns:
            df_daily = daily_data[ticker].copy()
            df_daily['Ticker'] = ticker
            all_daily_dfs.append(df_daily)
            
    df_daily_combined = pd.concat(all_daily_dfs).sort_index() if all_daily_dfs else pd.DataFrame()
    
    # Reset index to save it to the database table
    df_daily_combined.reset_index(inplace=True)
    df_daily_combined.rename(columns={'index': 'Date'}, inplace=True)

    # Store the fetched data in the database
    save_prices_to_db(df_daily_combined)
    
    return df_daily_combined

@st.cache_data(ttl=3600)  # Cache the data for 1 hour
def get_all_prices_cached(tickers):
    """
    Tries to load data from the database first. If the database is empty,
    it fetches new data from the API and populates the database.
    """
    # 1. Try to load data from the database
    df_daily_combined = load_prices_from_db()
    
    # 2. If the database is empty, fetch new data from the API
    if df_daily_combined.empty:
        df_daily_combined = fetch_and_store_prices(tickers)
    
    return df_daily_combined

def load_all_prices():
    """
    Loads followed tickers and then retrieves cached data.
    """
    tickers_df = load_followed_tickers()
    if tickers_df.empty:
        return pd.DataFrame()
    
    tickers = tickers_df['Ticker'].tolist()
    
    df_daily = get_all_prices_cached(tickers)
    
    return df_daily             










