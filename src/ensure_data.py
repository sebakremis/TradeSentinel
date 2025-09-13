# src/ensure_data.py
from datetime import datetime
import pandas as pd
from typing import List, Dict
from storage import load_prices, save_prices
from data_fetch import get_market_data
from log_utils import info, warn, error

def ensure_prices(
    tickers: List[str],
    interval: str = "1m",
    lookback_days: int = 5
) -> Dict[str, pd.DataFrame]:
    """
    Ensure we have up-to-date prices for each ticker.
    Falls back to daily closes if intraday data is empty.
    """
    results = {}
    for ticker in tickers:
        local_df = load_prices(ticker, interval)

        if local_df.empty:
            fresh = get_market_data([ticker], interval=interval, period=f"{lookback_days}d")
            if fresh.empty and interval != "1d":
                warn(f"No intraday data for {ticker}, falling back to daily close.")
                fresh = get_market_data([ticker], interval="1d", period=f"{lookback_days}d")
            if not fresh.empty:
                save_prices(ticker, interval, fresh)
            results[ticker] = fresh
            continue

        last_ts = local_df.index.max()
        now = datetime.utcnow()

        if last_ts is None or (now - last_ts).total_seconds() > 60:
            start_str = (last_ts + pd.Timedelta(minutes=1)).strftime("%Y-%m-%d")
            fresh = get_market_data([ticker], interval=interval, start=start_str)
            if fresh.empty and interval != "1d":
                warn(f"No intraday update for {ticker}, falling back to daily close.")
                fresh = get_market_data([ticker], interval="1d", period=f"{lookback_days}d")
            if not fresh.empty:
                combined = pd.concat([local_df, fresh])
                combined = combined[~combined.index.duplicated(keep="last")].sort_index()
                save_prices(ticker, interval, combined)
                results[ticker] = combined
            else:
                results[ticker] = local_df
        else:
            results[ticker] = local_df

    return results

def as_close_panel(price_map: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Convert a dict of price DataFrames into a single DataFrame of Close prices.
    Handles both single-index and multi-index column formats from yfinance.
    """
    closes = []
    for ticker, df in price_map.items():
        if df.empty:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            if (ticker, "Close") in df.columns:
                closes.append(df[(ticker, "Close")].rename(ticker))
        elif "Close" in df.columns:
            closes.append(df["Close"].rename(ticker))
    if closes:
        return pd.concat(closes, axis=1).sort_index()
    return pd.DataFrame()
