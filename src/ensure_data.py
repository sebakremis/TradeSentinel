# src/ensure_data.py
"""
ensure_data.py
==============

Utility for retrieving and validating historical market price data for one or
more tickers using the Yahoo Finance API via the `yfinance` library.

This module provides a single function, `ensure_prices`, which downloads price
data for the specified tickers, ensures that a 'Close' column is present in the
result, and returns the data in a dictionary keyed by ticker symbol.

Features
--------
- Fetches historical OHLCV data for each ticker.
- Supports configurable `period` and `interval` parameters.
- Automatically adjusts prices to account for corporate actions (splits, dividends).
- Ensures a 'Close' column exists:
  - If missing but 'Adj Close' is present, uses 'Adj Close' as a substitute.
  - Skips tickers with neither 'Close' nor 'Adj Close'.
- Logs progress, warnings, and errors using `log_utils` functions.

Functions
---------
- `ensure_prices(tickers: list[str], period: str = "5d", interval: str = "1d") -> dict[str, pandas.DataFrame]`  
  Download and validate price data for the given tickers.

Parameters
----------
tickers : list[str]
    List of ticker symbols to fetch.
period : str, optional
    Data period to download (e.g., '1d', '5d', '1mo', '1y', 'max').
interval : str, optional
    Data interval (e.g., '1m', '5m', '1h', '1d', '1wk', '1mo').

Returns
-------
dict[str, pandas.DataFrame]
    Mapping of ticker symbol to its corresponding DataFrame containing at least
    a 'Close' column.

Dependencies
------------
- yfinance
- pandas (implied via yfinance output)
- log_utils (for logging)
- colorama (indirectly, via log_utils)

Usage Example
-------------
    from ensure_data import ensure_prices

    tickers = ["AAPL", "MSFT", "GOOG"]
    prices = ensure_prices(tickers, period="1mo", interval="1d")

    for symbol, df in prices.items():
        print(symbol, df.tail())

Notes
-----
- If a ticker returns no data, it is skipped with a warning.
- Any exceptions during download are caught and logged as errors.
"""

import yfinance as yf
from log_utils import info, warn, error

def ensure_prices(tickers, period="5d", interval="1d"):
    """
    Fetch historical price data for each ticker and ensure a 'Close' column exists.
    Returns:
        dict[str, pd.DataFrame]: Mapping of ticker -> DataFrame with at least a 'Close' column.
    """
    prices = {}
    for ticker in tickers:
        try:
            info(f"Fetching data for {ticker}...")
            df = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True  # ✅ Explicit to avoid FutureWarning
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

            prices[ticker] = df

        except Exception as e:
            error(f"Error fetching data for {ticker}: {e}")

    return prices

