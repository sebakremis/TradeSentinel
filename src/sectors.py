# src/sectors.py
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"



def load_followed_tickers() -> pd.DataFrame:
    """
    Load followed tickers and their sectors from CSV.
    Returns DataFrame with columns: Ticker, Sector
    """
    fp = DATA_DIR / "followed_tickers.csv"
    if not fp.exists():
        return pd.DataFrame(columns=["Ticker", "Sector"])

    df = pd.read_csv(fp)

    # Normalize tickers
    df["Ticker"] = df["Ticker"].str.upper()

    # Ensure Sector column exists
    if "Sector" not in df.columns:
        df["Sector"] = "Unknown"

    return df

sector_map = get_sector_map(tickers)