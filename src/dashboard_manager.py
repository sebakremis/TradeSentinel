# src/dashboard_manager.py
from data_fetch import get_market_data
from storage import save_prices_incremental

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
import pandas as pd


def process_dashboard_data(interval: str) -> pd.DataFrame:
    df = load_all_prices(interval)

    if df.empty:
        return df

    # If columns are MultiIndex (ticker, field), flatten them
    if isinstance(df.columns, pd.MultiIndex):
        # Move ticker from columns into rows
        df = df.stack(level=0).reset_index()
        df = df.rename(columns={"level_1": "Ticker"})
    else:
        # If already flat, just ensure Ticker column exists
        if "Ticker" not in df.columns:
            df["Ticker"] = None

    # Standardize column order
    cols = ["Date", "Ticker", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
    df = df[[c for c in cols if c in df.columns]]

    df["Interval"] = interval
    return df


