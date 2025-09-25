# src/data_manager.py
import pandas as pd
import yfinance as yf
import streamlit as st
import datetime as dt
from src.tickers_manager import load_followed_tickers
import pandas as pd
from pathlib import Path
from log_utils import info, warn, error

# Directory for storing per-ticker CSVs
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "market_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_ticker_file(ticker: str) -> Path:
    """Return the file path for a given ticker's CSV."""
    return DATA_DIR / f"{ticker.upper()}.csv"


def fetch_and_store_ticker(ticker: str, start_date=None, end_date=None,
                           interval: str = "1d", period: str = "1y") -> pd.DataFrame:
    """
    Fetch data for a ticker using data_fetch.get_market_data().
    Store it in /data/market_data/<TICKER>.csv if not already present.
    Returns the DataFrame.
    """
    file_path = get_ticker_file(ticker)

    if file_path.exists():
        return pd.read_csv(file_path, parse_dates=["Date"])

    # Fetch fresh data (note: get_market_data expects a list of tickers)
    df = data_fetch.get_market_data([ticker], start=start_date, end=end_date,
                                    interval=interval, period=period)

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(0)

    # Ensure Date is a column, not just the index
    df = df.reset_index()

    # Save to CSV
    df.to_csv(file_path, index=False)
    return df


def load_ticker_data(ticker: str, start_date=None, end_date=None,
                     interval: str = "1d", period: str = "1y") -> pd.DataFrame:
    """
    Load ticker data from file if it exists, else fetch and store it.
    """
    file_path = get_ticker_file(ticker)
    if file_path.exists():
        return pd.read_csv(file_path, parse_dates=["Date"])
    return fetch_and_store_ticker(ticker, start_date, end_date, interval, period)


# From former data_fetch.py module
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
    
# from former storage.py module
def save_prices_incremental(ticker: str, interval: str, new_data: pd.DataFrame):
    """
    Save price data incrementally for a single ticker/interval,
    ensuring all columns are preserved and handling the index correctly.
    """
    interval_dir = DATA_DIR / "prices" / interval
    interval_dir.mkdir(parents=True, exist_ok=True)
    fp = interval_dir / f"{ticker.upper()}.parquet"

    df = new_data.copy()

    # Flatten the multi-level column DataFrame if it exists.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(1)

    # Ensure the index is a DatetimeIndex and has a name
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    
    # Set the index name to 'Date'
    df.index.name = "Date"
    df.dropna(subset=[df.index.name], inplace=True)
    
    # Add the 'Ticker' column to the new data
    df['Ticker'] = ticker

    # Merge with existing file if present
    if fp.exists():
        try:
            # Load old data and set 'Date' as the index for merging
            old = pd.read_parquet(fp).set_index("Date")
            old.index = pd.to_datetime(old.index)
            
            # Concatenate and handle duplicates, keeping the most recent data
            combined = pd.concat([old, df])
            combined = combined[~combined.index.duplicated(keep="last")]
            combined = combined.sort_index()
        except Exception as e:
            st.warning(f"Error reading {fp}: {e}. Overwriting file.")
            combined = df.sort_index()
    else:
        combined = df.sort_index()

    # Drop any columns that are all NaN
    combined = combined.dropna(axis=1, how='all')

    # Save the DataFrame with 'Date' as a regular column
    combined.reset_index(inplace=True)
    combined.to_parquet(fp)
    
    # The last date of the data is now in the 'Date' column
    if not combined.empty and "Date" in combined.columns:
        last_date = combined["Date"].max().date()


# from former ensure_data.py module

# Cache to avoid repeated sector lookups
_sector_cache = {}

def _get_sector(ticker: str) -> str:
    """Fetch sector for a ticker, with caching and graceful fallback."""
    if ticker in _sector_cache:
        return _sector_cache[ticker]

    sector = "Unknown"
    try:
        yf_t = yf.Ticker(ticker)
        try:
            info_dict = yf_t.get_info()
        except Exception:
            info_dict = getattr(yf_t, "info", {}) or {}
        if isinstance(info_dict, dict):
            sector = info_dict.get("sector") or "Unknown"
    except Exception as e:
        warn(f"Could not fetch sector for {ticker}: {e}")

    _sector_cache[ticker] = sector
    return sector

def ensure_prices(tickers, period="5d", interval="1d"):
    """
    Fetch historical price data for each ticker, ensure 'Close' exists,
    flatten columns if needed, and add a 'Sector' column.

    Returns:
        dict[ticker -> DataFrame] with flat column names
    """
    prices = {}
    for ticker in tickers:
        try:
            info(f"Fetching data for {ticker} ...")
            # Force single-ticker mode and request flat columns
            df = yf.download(
                str(ticker),
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
                group_by='column'  # prevent MultiIndex where possible
            )

            if df.empty:
                warn(f"No data returned for {ticker}, skipping.")
                continue

            # Ensure 'Close' column exists
            if "Close" not in df.columns:
                if "Adj Close" in df.columns:
                    warn(f"'Close' missing for {ticker}, using 'Adj Close' instead.")
                    df["Close"] = df["Adj Close"]
                else:
                    error(f"No 'Close' or 'Adj Close' column for {ticker}, skipping.")
                    continue

            # Add sector as a constant column
            df["Sector"] = _get_sector(ticker)

            # Flatten columns immediately after adding Sector
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

            prices[ticker] = df

        except Exception as e:
            error(f"Error fetching data for {ticker}: {e}")

    return prices