# src/data_manager.py
import pandas as pd
from pathlib import Path
import data_fetch  # existing module

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "market_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_ticker_file(ticker: str) -> Path:
    """Return the file path for a given ticker's CSV."""
    return DATA_DIR / f"{ticker.upper()}.csv"

def fetch_and_store_ticker(ticker: str, start_date=None, end_date=None):
    file_path = get_ticker_file(ticker)

    if file_path.exists():
        return pd.read_csv(file_path, parse_dates=True)

    # FIX: call get_market_data instead of fetch_data
    df = data_fetch.get_market_data([ticker], start=start_date, end=end_date, interval="1d", period="1y")
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

