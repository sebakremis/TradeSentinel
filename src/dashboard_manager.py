# src/dashboard_manager.py

import pandas as pd
from src.config import BASE_DIR

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


# Active mapping used by main.py for dashboard data
intervals_main = {
    "60d": "30m",
    "1y": "1d"
}

# Full interval mapping
intervals_full = {
    "1d":  ["1m", "5m", "15m", "30m", "1h"],
    "5d":  ["5m", "15m", "30m", "1h", "1d"],
    "1mo": ["15m", "30m", "1h", "1d", "1wk"],
    "3mo": ["15m", "30m", "1h", "1d", "1wk"],
    "6mo": ["1d", "1wk", "1mo"],
    "1y":  ["1d", "1wk", "1mo"],
    "ytd": ["1d", "1wk", "1mo"],
    "max": ["1d", "1wk", "1mo"]
}










