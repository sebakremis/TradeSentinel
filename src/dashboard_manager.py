# src/dashboard_manager.py
from src.data_fetch import get_market_data
from src.storage import save_prices_incremental
import pandas as pd
from src.storage import load_all_prices

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




def process_dashboard_data(interval: str) -> pd.DataFrame:
    df = load_all_prices(interval)
    if df.empty:
        return df

    # Ensure Date is index
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.set_index("Date")

    # Keep only standard columns
    cols = ["Ticker", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
    df = df[[c for c in cols if c in df.columns]].copy()

    # Add interval
    df["Interval"] = interval

    return df










