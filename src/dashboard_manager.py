# src/dashboard_manager.py
import streamlit as st
import pandas as pd
import yfinance as yf
from log_utils import info, warn, error

from src.database_manager import save_prices_to_db, load_prices_from_db
from src.config import MAIN_DB_NAME, DATA_DIR
from src.indicators import calculate_price_change, ema, trend, highest_close, distance_highest_close, annualized_metrics

# The database name is now a constant imported from database_manager
DB_NAME = MAIN_DB_NAME

def load_all_prices() -> pd.DataFrame:
    """A wrapper to load data from the main database."""
    return load_prices_from_db(MAIN_DB_NAME)

@st.cache_data(ttl=3600)
def get_all_prices_cached(tickers: list, period: str, interval: str) -> pd.DataFrame:
    """Fetches and caches all ticker data from yfinance and returns a single DataFrame."""
    info(f"Fetching data for {len(tickers)} tickers...")
    try:
        data = yf.download(
            tickers=tickers,
            period=period,
            interval=interval,
            group_by='ticker',
            auto_adjust=True,
            threads=True,
            progress=False
        )
    except Exception as e:
        error(f"Error fetching data from yfinance: {e}")
        return pd.DataFrame()

    if data.empty:
        warn("No data returned from yfinance.")
        return pd.DataFrame()
    
    df_list = []
    
    # We will now standardize the column creation AFTER the data is in a list of DataFrames
    if isinstance(data.columns, pd.MultiIndex):
        # Multi-ticker case
        for ticker in tickers:
            if ticker in data.columns.get_level_values(0):
                df = data[ticker].copy().reset_index()
                df['Ticker'] = ticker
                df_list.append(df)
    else:
        # Single-ticker case
        df = data.copy().reset_index()
        df['Ticker'] = tickers[0]
        df_list.append(df)
    
    if not df_list:
        warn("No data processed from fetched results. Returning an empty DataFrame.")
        return pd.DataFrame()

    combined_df = pd.concat(df_list, ignore_index=True)

    # **Crucial Fix:** Standardize the 'Date' or 'index' column to 'Datetime'
    if 'Date' in combined_df.columns:
        combined_df.rename(columns={'Date': 'Datetime'}, inplace=True)
    elif 'index' in combined_df.columns:
        combined_df.rename(columns={'index': 'Datetime'}, inplace=True)
    
    # Check if a 'Datetime' column now exists before proceeding
    if 'Datetime' in combined_df.columns:
        combined_df['Date'] = combined_df['Datetime'].dt.date
        combined_df['Time'] = combined_df['Datetime'].dt.time
        combined_df.drop(columns=['Datetime'], inplace=True)
    else:
        # This case should now be impossible, but it's a good fail-safe
        error("The 'Datetime' column was not found after renaming. Data processing failed.")
        return pd.DataFrame()

    # Save the finalized DataFrame to the main dashboard database
    save_prices_to_db(combined_df, MAIN_DB_NAME)
    info("✅ Data fetched and saved to database.")

    # Return the combined DataFrame for use in the dashboard
    return combined_df          


@st.cache_data(show_spinner="Calculating indicators...")
def calculate_all_indicators(df_daily, fast_n, slow_n)-> pd.DataFrame:
    # Apply all calculation functions here
    df_daily = calculate_price_change(df_daily)
    df_daily = trend(df_daily, fast_n, slow_n)
    df_daily = ema(df_daily, fast_n)
    df_daily = highest_close(df_daily)
    df_daily = distance_highest_close(df_daily)
    df_daily = annualized_metrics(df_daily, n_days=200)
    
    return df_daily








