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
    """Load all parquet files for a given interval and return as a combined DataFrame."""
    interval_dir = BASE_DIR / interval
    frames = []
    if interval_dir.exists():
        for file_path in interval_dir.glob("*.parquet"):
            try:
                df = pd.read_parquet(file_path)
                ticker = file_path.stem  # filename without extension
                df["Ticker"] = ticker
                df["Interval"] = interval   # ✅ tag the interval
                frames.append(df)
            except Exception as e:
                st.warning(f"⚠️ Could not load {file_path.name}: {e}")
    if frames:
        return pd.concat(frames)
    return pd.DataFrame()



def save_prices_incremental(ticker: str, interval: str, df):
    from pathlib import Path
    import pandas as pd

    interval_dir = Path("data/prices") / interval
    interval_dir.mkdir(parents=True, exist_ok=True)
    file_path = interval_dir / f"{ticker}.parquet"

    if file_path.exists():
        existing = pd.read_parquet(file_path)
        combined = pd.concat([existing, df])
        combined = combined[~combined.index.duplicated(keep="last")]
        combined.sort_index(inplace=True)

        if not combined.empty:
            combined.to_parquet(file_path, engine="pyarrow", index=True)
            last_date = combined.index[-1]
            print(f"🔄 Updated {ticker} {interval} data up to {last_date}")
        else:
            print(f"⚠️ No data to update for {ticker} {interval}")
    else:
        if df is not None and not df.empty:
            df.to_parquet(file_path, engine="pyarrow", index=True)
            last_date = df.index[-1]
            print(f"✅ Created new file for {ticker} {interval} up to {last_date}")
        else:
            print(f"⚠️ No data fetched for {ticker} {interval}, nothing saved.")




