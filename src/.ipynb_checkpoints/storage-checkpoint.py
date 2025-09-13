# src/storage.py

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

