# src/data_fetching.py
import yfinance as yf
import pandas as pd
import streamlit as st
from src.log_utils import info, warn
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
# 🚨 UPDATED SIGNATURE: Add 'start' and 'end' as optional keyword arguments
def get_portfolio_data_cached(tickers: list, interval: str, period: str = None, start: str = None, end: str = None) -> dict:
    """
    Fetches historical data for portfolio tickers from yfinance.
    
    It accepts either a 'period' string OR 'start' and 'end' date strings.
    
    Returns:
        dict: A dictionary of DataFrames, keyed by ticker symbol.
    """
    
    # 🚨 DYNAMIC KWARGS FOR yf.download
    # Base arguments for yfinance
    yf_kwargs = {
        'tickers': tickers,
        'interval': interval,
        'group_by': 'ticker',
        'auto_adjust': True,
        'threads': True,
        'progress': False
    }

    # Add time constraints based on provided arguments
    if period:
        # Scenario 1: Preset period (e.g., '1y') is provided
        yf_kwargs['period'] = period
        info(f"Fetching data from API for period={period}, interval={interval}...")
    elif start:
        # Scenario 2: Custom date(s) are provided
        yf_kwargs['start'] = start
        if end:
            yf_kwargs['end'] = end
            info(f"Fetching data from API for start={start} to end={end}, interval={interval}...")
        else:
            info(f"Fetching data from API starting at={start}, interval={interval}...")
    else:
        # Fallback if no time constraint is given (shouldn't happen with our frontend logic)
        yf_kwargs['period'] = '1y'
        info(f"Fetching data from API for default period=1y, interval={interval}...")
        
    
    try:
        # 🚨 Use the dynamically created yf_kwargs dictionary
        raw_data = yf.download(**yf_kwargs)
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
        sector = _get_sector(ticker) # Assuming _get_sector is defined elsewhere

        df = None
        if is_multi_ticker:
            if (ticker, 'Close') in raw_data.columns:
                df = raw_data[ticker].copy()
        else: # Single ticker case
            # Check if this is the ticker requested, as raw_data is not MultiIndex
            if 'Close' in raw_data.columns and len(tickers) == 1 and tickers[0] == ticker:
                df = raw_data.copy()

        if df is not None and 'Close' in df.columns:
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            # Ensure 'Adj Close' is used if 'Close' is missing (or use 'Close' if present)
            # Since auto_adjust=True, we rely on the remaining 'Close' column being the adjusted price.
            # However, yfinance sometimes renames 'Adj Close' to 'Close' or returns both.
            if 'Close' not in df.columns and 'Adj Close' in df.columns:
                 df.rename(columns={'Adj Close': 'Close'}, inplace=True)

            # Drop other columns (Open, High, Low, Volume) to keep data clean
            df.drop(columns=[col for col in ['Open', 'High', 'Low', 'Volume', 'Adj Close'] if col in df.columns], 
                    inplace=True, errors='ignore')

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
        save_prices_to_db(combined_df, DB_NAME) # Assuming save_prices_to_db is defined elsewhere

    return processed_prices