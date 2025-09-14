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

def load_prices(ticker: str, interval: str) -> pd.DataFrame:
    """Load stored prices for a ticker/interval, or return empty DataFrame if none."""
    fp = _file_path(ticker, interval)
    if fp.exists():
        return pd.read_parquet(fp)
    return pd.DataFrame()

def save_prices(ticker: str, interval: str, df: pd.DataFrame) -> None:
    """Save prices to local storage, merging with existing data if present."""
    fp = _file_path(ticker, interval)
    if fp.exists():
        existing = pd.read_parquet(fp)
        df = pd.concat([existing, df])
    # Remove duplicates and sort
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_parquet(fp)

