# src/storage.py
"""
storage.py
==========

Local storage utilities for persisting and retrieving historical price data
in Parquet format, organized by ticker symbol and interval.

This module provides helper functions to:
- Construct consistent file paths for storing price data.
- Load previously saved price data for a given ticker/interval.
- Save new price data, merging with existing records while removing duplicates.

Data is stored under the `data/prices/<interval>/` directory, with one Parquet
file per ticker.

Features
--------
- **Automatic Directory Creation**:
  Ensures the appropriate folder exists before saving data.

- **Efficient Storage**:
  Uses Apache Parquet format for compact, fast read/write operations.

- **Data Merging**:
  When saving, merges new data with existing data, removes duplicate index
  entries (keeping the latest), and sorts by index.

Functions
---------
- `_file_path(ticker: str, interval: str) -> pathlib.Path`  
  Return the file path for the given ticker and interval, creating directories
  if necessary.

- `load_prices(ticker: str, interval: str) -> pandas.DataFrame`  
  Load stored prices for a ticker/interval, or return an empty DataFrame if no
  file exists.

- `save_prices(ticker: str, interval: str, df: pandas.DataFrame) -> None`  
  Save prices to local storage, merging with existing data if present.

Dependencies
------------
- pandas
- pathlib (standard library)

Usage Example
-------------
    from storage import load_prices, save_prices
    import pandas as pd

    # Load existing data
    df = load_prices("AAPL", "1d")

    # Append new data and save
    new_data = pd.DataFrame({...})
    save_prices("AAPL", "1d", new_data)

Notes
-----
- The DataFrame index is expected to be datetime-like for proper sorting.
- Duplicate index entries are resolved by keeping the last occurrence.
"""

from pathlib import Path
import pandas as pd

# Base folder for storing price data
BASE_DIR = Path("data/prices")

def _file_path(ticker: str, interval: str) -> Path:
    """Return the file path for a given ticker and interval."""
    folder = BASE_DIR / interval
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{ticker}.parquet"


def load_all_prices(interval: str) -> pd.DataFrame:
    """
    Load all tickers for a given interval into long format.
    Each parquet file is one ticker; we add a Ticker column and concat.
    """
    interval_dir = BASE_DIR / interval
    if not interval_dir.exists():
        return pd.DataFrame()

    frames = []
    for fp in interval_dir.glob("*.parquet"):
        ticker = fp.stem.upper()
        df = pd.read_parquet(fp)
        if df.empty:
            continue

        # Ensure Date index
        if not isinstance(df.index, pd.DatetimeIndex):
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                df = df.set_index("Date")
        df.index.name = "Date"

        # Add ticker column
        df["Ticker"] = ticker

        # Drop rows with no OHLCV values
        value_cols = [c for c in ["Open", "High", "Low", "Close", "Adj Close", "Volume"] if c in df.columns]
        if value_cols:
            df = df.dropna(subset=value_cols, how="all")

        frames.append(df)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames).sort_index()




def save_prices_incremental(ticker: str, interval: str, new_data: pd.DataFrame):
    """
    Save price data incrementally for a single ticker/interval.
    Ensures flat schema: Date index, OHLCV columns, no prefixed names.
    """
    interval_dir = BASE_DIR / interval
    interval_dir.mkdir(parents=True, exist_ok=True)

    fp = interval_dir / f"{ticker.upper()}.parquet"

    # Normalize new_data
    df = new_data.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.set_index("Date")
    df.index.name = "Date"

    # Drop any ticker prefixes in columns (e.g. "PLTR_Open")
    df.columns = [c.split("_")[-1] if "_" in c else c for c in df.columns]

    # Keep only standard OHLCV columns
    keep = [c for c in ["Open", "High", "Low", "Close", "Adj Close", "Volume"] if c in df.columns]
    df = df[keep]

    # Load existing file if present
    if fp.exists():
        old = pd.read_parquet(fp)
        old.index = pd.to_datetime(old.index)
        combined = pd.concat([old, df])
        combined = combined[~combined.index.duplicated(keep="last")]
        combined = combined.sort_index()
    else:
        combined = df.sort_index()

    combined.to_parquet(fp)
    print(f"✅ Saved {ticker} {interval} up to {combined.index.max()}")





