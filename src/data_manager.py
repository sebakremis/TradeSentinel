# src/data_manager.py
import pandas as pd
from pathlib import Path
import data_fetch  # existing module

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "market_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_ticker_file(ticker: str) -> Path:
    """Return the file path for a given ticker's CSV."""
    return DATA_DIR / f"{ticker.upper()}.csv"

def fetch_and_store_ticker(ticker: str, start_date=None, end_date=None) -> pd.DataFrame:
    """
    Fetch data for a ticker using existing data_fetch module.
    Store it in /data/market_data/<TICKER>.csv if not already present.
    Returns the DataFrame.
    """
    file_path = get_ticker_file(ticker)

    if file_path.exists():
        return pd.read_csv(file_path, parse_dates=True)

    # Fetch fresh data
    df = data_fetch.fetch_data(ticker, start_date, end_date)
    df.to_csv(file_path, index=False)
    return df

def load_ticker_data(ticker: str, start_date=None, end_date=None) -> pd.DataFrame:
    """
    Load ticker data from file if it exists, else fetch and store it.
    """
    file_path = get_ticker_file(ticker)
    if file_path.exists():
        return pd.read_csv(file_path, parse_dates=True)
    return fetch_and_store_ticker(ticker, start_date, end_date)

