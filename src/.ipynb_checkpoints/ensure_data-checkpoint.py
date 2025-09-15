# src/ensure_data.py
"""
ensure_data.py
==============

Utility for retrieving, validating, and enriching historical market price data
for one or more tickers using the Yahoo Finance API via the `yfinance` library.

Features
--------
- Fetches historical OHLCV data for each ticker in **single‑ticker mode** to avoid MultiIndex columns.
- Supports configurable `period` and `interval` parameters.
- Automatically adjusts prices for corporate actions (splits, dividends).
- Ensures a 'Close' column exists:
  - If missing but 'Adj Close' is present, uses 'Adj Close' as a substitute.
  - Skips tickers with neither 'Close' nor 'Adj Close'.
- Enriches each DataFrame with a constant 'Sector' column from yfinance metadata.
- Caches sector lookups per run to minimize HTTP calls.
- Flattens any MultiIndex columns immediately after adding 'Sector'.
- Logs progress, warnings, and errors using `log_utils` functions.

Functions
---------
- ensure_prices(tickers: list[str], period: str = "5d", interval: str = "1d")
    Download and validate price data for the given tickers and append 'Sector'.

Returns
-------
dict[str, pandas.DataFrame]
    Mapping of ticker symbol to its corresponding DataFrame containing at least:
    - 'Close' (float)
    - 'Sector' (string)
    plus any other OHLCV columns returned by yfinance.

Dependencies
------------
- yfinance
- pandas (implied via yfinance output)
- log_utils (for logging)

Notes
-----
- If a ticker returns no data, it is skipped with a warning.
- Any exceptions during download or sector lookup are caught and logged.
- Sector lookups are best‑effort; failures result in Sector="Unknown" but do not
  prevent price data from being returned.
"""

import pandas as pd
import yfinance as yf
from log_utils import info, warn, error

# Cache to avoid repeated sector lookups
_sector_cache = {}

def _get_sector(ticker: str) -> str:
    """Fetch sector for a ticker, with caching and graceful fallback."""
    if ticker in _sector_cache:
        return _sector_cache[ticker]

    sector = "Unknown"
    try:
        yf_t = yf.Ticker(ticker)
        try:
            info_dict = yf_t.get_info()
        except Exception:
            info_dict = getattr(yf_t, "info", {}) or {}
        if isinstance(info_dict, dict):
            sector = info_dict.get("sector") or "Unknown"
    except Exception as e:
        warn(f"Could not fetch sector for {ticker}: {e}")

    _sector_cache[ticker] = sector
    return sector

def ensure_prices(tickers, period="5d", interval="1d"):
    """
    Fetch historical price data for each ticker, ensure 'Close' exists,
    flatten columns if needed, and add a 'Sector' column.

    Returns:
        dict[ticker -> DataFrame] with flat column names
    """
    prices = {}
    for ticker in tickers:
        try:
            info(f"Fetching data for {ticker} ...")
            # Force single-ticker mode and request flat columns
            df = yf.download(
                str(ticker),
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
                group_by='column'  # prevent MultiIndex where possible
            )

            if df.empty:
                warn(f"No data returned for {ticker}, skipping.")
                continue

            # Ensure 'Close' column exists
            if "Close" not in df.columns:
                if "Adj Close" in df.columns:
                    warn(f"'Close' missing for {ticker}, using 'Adj Close' instead.")
                    df["Close"] = df["Adj Close"]
                else:
                    error(f"No 'Close' or 'Adj Close' column for {ticker}, skipping.")
                    continue

            # Add sector as a constant column
            df["Sector"] = _get_sector(ticker)

            # Flatten columns immediately after adding Sector
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

            prices[ticker] = df

        except Exception as e:
            error(f"Error fetching data for {ticker}: {e}")

    return prices













