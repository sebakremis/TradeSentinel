# src/data_fetching.py
import yfinance as yf
import pandas as pd
import streamlit as st
from log_utils import info, warn
from src.database_manager import save_prices_to_db
DB_NAME = 'portfolio_data.db'

@st.cache_data(ttl=86400) # Cache sector data for 24 hours
def _get_sector(ticker: str) -> str:
    """Fetch sector for a ticker using yfinance, with caching."""
    try:
        yf_t = yf.Ticker(ticker)
        info_dict = yf_t.info or {}
        sector = info_dict.get("sector", "Unknown")
    except Exception as e:
        warn(f"Could not fetch sector for {ticker}: {e}")
        sector = "Unknown"
    return sector

@st.cache_data(ttl=3600)
def get_portfolio_data_cached(tickers: list, period: str, interval: str) -> dict:
    """
    Fetches historical data for portfolio tickers from yfinance.
    Streamlit cache key is based on (tickers, period, interval).
    Data is saved to the internal database for long-term storage.
    
    The complex database pre-check is removed to ensure the Streamlit
    cache key (which includes 'period') works correctly to get fresh data
    for a new period.
    """
    
    info(f"Fetching data from API for period={period}, interval={interval}...")
    
    try:
        raw_data = yf.download(
            tickers=tickers,
            period=period,
            interval=interval,
            group_by='ticker',
            auto_adjust=True,
            threads=True,
            progress=False
        )
    except Exception as e:
        st.error(f"Error fetching data from yfinance: {e}")
        return {}

    if raw_data.empty:
        st.warning("No data returned from yfinance.")
        return {}

    # Process and save to database
    all_data_for_db = []
    processed_prices = {}
    
    # Determine if the data has a MultiIndex (multiple tickers) or a regular index (single ticker)
    is_multi_ticker = isinstance(raw_data.columns, pd.MultiIndex)
    
    for ticker in tickers:
        sector = _get_sector(ticker)

        df = None
        if is_multi_ticker:
            if (ticker, 'Close') in raw_data.columns:
                df = raw_data[ticker].copy()
        else: # Single ticker case
            if 'Close' in raw_data.columns and len(tickers) == 1 and tickers[0] == ticker:
                df = raw_data.copy()

        if df is not None and 'Close' in df.columns:
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            df['Ticker'] = ticker
            df['Sector'] = sector # Add sector column
            processed_prices[ticker] = df
            
            # For database storage, reset index and rename
            df_for_db = df.reset_index(names=['Date'])
            df_for_db['Date'] = df_for_db['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
            all_data_for_db.append(df_for_db)
        else:
            warn(f"No valid data found for {ticker}, skipping.")

    if all_data_for_db:
        combined_df = pd.concat(all_data_for_db, ignore_index=True)
        save_prices_to_db(combined_df, DB_NAME)

    return processed_prices