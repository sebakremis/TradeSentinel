# src/storage.py
"""
storage.py
==========

Local storage utilities for persisting and retrieving historical price data
in Parquet format, organized by ticker symbol and interval.
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
        df = pd.read_parquet(fp)
        if df.empty:
            continue
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    # Concatenate all DataFrames and sort by index
    combined_df = pd.concat(frames)

    # Clean up the combined DataFrame before returning
    if "Date" in combined_df.columns:
        combined_df = combined_df.set_index("Date")
    combined_df.index = pd.to_datetime(combined_df.index).tz_localize(None)
    combined_df.index.name = "Date"
    
    # Drop rows with no OHLCV values
    value_cols = [c for c in ["Open", "High", "Low", "Close", "Adj Close", "Volume"] if c in combined_df.columns]
    if value_cols:
        combined_df = combined_df.dropna(subset=value_cols, how="all")

    return combined_df.sort_index()


def save_prices_incremental(ticker: str, interval: str, new_data: pd.DataFrame):
    """
    Save price data incrementally for a single ticker/interval.
    """
    interval_dir = BASE_DIR / interval
    interval_dir.mkdir(parents=True, exist_ok=True)
    fp = interval_dir / f"{ticker.upper()}.parquet"

    df = new_data.copy()

    # Flatten MultiIndex columns if needed
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join([str(c) for c in col if c]) for col in df.columns]

    # Normalize column names
    rename_map = {
        "Open": "Open", "High": "High", "Low": "Low", "Close": "Close",
        "Adj Close": "Adj Close", "Volume": "Volume"
    }
    for col in list(df.columns):
        for base in rename_map:
            if col.endswith(base):
                df = df.rename(columns={col: base})

    # Ensure Date index
    if not isinstance(df.index, pd.DatetimeIndex):
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.set_index("Date")
    df.index.name = "Date"

    # MERGE WITH EXISTING FILE IF PRESENT (RETAIN ALL COLUMNS)
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






