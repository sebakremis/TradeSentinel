# src/data_fetch.py

import pandas as pd
import yfinance as yf
import io
import contextlib
import os

# Your SECTOR_CSV_PATH and load_sector_data() functions are assumed to be correct
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SECTOR_CSV_PATH = os.path.join(SCRIPT_DIR, "..", "data", "followed_tickers_sectors.csv")

def load_sector_data():
    # ... (Your working load_sector_data function here)
    try:
        df = pd.read_csv(SECTOR_CSV_PATH)
        sector_dict = df.set_index('Ticker')['Sector'].to_dict()
        return sector_dict
    except Exception as e:
        print(f"❌ Error loading sector data: {e}")
        return {}
        
SECTOR_DATA = load_sector_data()

def get_market_data(
    ticker: str,
    interval: str = "1d",
    period: str = "1y",
    start: str = None,
    end: str = None
) -> pd.DataFrame:
    """
    Fetch market data for a ticker from Yahoo Finance, calculate Adj Close,
    and add sector data from a local CSV.
    """
    clean_ticker = ticker.strip().upper()

    stderr_buffer = io.StringIO()
    with contextlib.redirect_stderr(stderr_buffer):
        try:
            ticker_obj = yf.Ticker(clean_ticker)
            df = ticker_obj.history(
                interval=interval,
                period=None if start else period,
                start=start,
                end=end,
                # Explicitly disable auto_adjust to avoid inconsistencies
                auto_adjust=False,
            )
        except Exception as e:
            print(f"❌ Failed to fetch {clean_ticker}: {e}")
            return pd.DataFrame()

    if df.empty:
        print(f"⚠️ No data returned for {clean_ticker}")
        return pd.DataFrame()

    if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    # Manual calculation of Adjusted Close
    if "Adj Close" in df.columns and "Close" in df.columns:
        if not df["Adj Close"].empty and df["Adj Close"].iloc[-1] != df["Close"].iloc[-1]:
            # If both columns exist and are different, the scale factor is valid
            scale_factor = df["Adj Close"] / df["Close"]
            df["Adj Close"] = df["Close"] * scale_factor.fillna(method='ffill')
        else:
            # If Adj Close is missing or identical to Close, just copy Close
            df["Adj Close"] = df["Close"]

    # If Adj Close column doesn't exist at all, create it from Close
    elif "Close" in df.columns:
        df["Adj Close"] = df["Close"]
    
    # Get sector from the pre-loaded dictionary
    sector = SECTOR_DATA.get(clean_ticker, 'N/A')
    
    # Add the Ticker, Interval, and Sector columns to the DataFrame
    df["Ticker"] = clean_ticker
    df["Interval"] = interval
    df["Sector"] = sector
    
    return df



