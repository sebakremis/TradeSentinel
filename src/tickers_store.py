# src/tickers_store.py
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TICKERS_FILE = DATA_DIR / "followed_tickers.csv"

def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_followed_tickers() -> list[str]:
    """Load tickers from the CSV file."""
    if not TICKERS_FILE.exists():
        return []
    df = pd.read_csv(TICKERS_FILE)
    # Expecting a column named 'ticker'
    if "ticker" in df.columns:
        return df["ticker"].dropna().unique().tolist()
    # If the file is just a single column with no header
    return df.iloc[:, 0].dropna().unique().tolist()

def save_followed_tickers(tickers: list[str]) -> None:
    """Save tickers list to CSV."""
    ensure_data_dir()
    df = pd.DataFrame({"ticker": tickers})
    df.to_csv(TICKERS_FILE, index=False)

def add_ticker(ticker: str) -> None:
    """Add a ticker if not already present."""
    tickers = load_followed_tickers()
    if ticker not in tickers:
        tickers.append(ticker)
        save_followed_tickers(tickers)

def remove_ticker(ticker: str) -> None:
    """Remove a ticker if it exists."""
    tickers = load_followed_tickers()
    if ticker in tickers:
        tickers.remove(ticker)
        save_followed_tickers(tickers)
