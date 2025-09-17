# src/data_manager.py
import pandas as pd
from pathlib import Path
import data_fetch  # your existing module

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


