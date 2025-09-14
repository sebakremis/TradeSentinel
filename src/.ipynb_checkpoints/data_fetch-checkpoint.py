# src/data_fetch.py
"""
data_fetch.py
=============

Utility for retrieving intraday or historical market data for one or more
tickers from Yahoo Finance using the `yfinance` library, with clean logging
and suppression of raw HTTP error output.

This module provides a single function, `get_market_data`, which:
1. Downloads price data for the specified tickers and time range.
2. Suppresses verbose Yahoo Finance stderr messages, replacing them with
   concise, user‑friendly log entries.
3. Logs warnings when no data is returned or when Yahoo Finance sends a
   non‑fatal message.
4. Returns a pandas DataFrame containing the requested data.

Features
--------
- **Flexible Parameters**:
  - Supports `interval` (e.g., '1m', '5m', '1d', '1wk', '1mo').
  - Supports `period` (e.g., '1d', '5d', '1mo', '1y', 'max') or explicit
    `start`/`end` dates.
  - Automatically disables `period` when `start` is provided.

- **Clean Logging**:
  - INFO, WARN, and ERROR messages routed through `log_utils`.
  - Suppresses raw Yahoo Finance stderr output for cleaner console logs.

- **Data Normalization**:
  - Removes timezone information from datetime index for consistency.
  - Returns empty DataFrame if no data is available.

Functions
---------
- `get_market_data(tickers: list[str], interval: str = "1m", period: Optional[str] = "1d", start: Optional[str] = None, end: Optional[str] = None) -> pandas.DataFrame`  
  Fetch market data for given tickers from Yahoo Finance.

Parameters
----------
tickers : list[str]
    List of ticker symbols to fetch.
interval : str, optional
    Data interval (default: '1m').
period : str, optional
    Data period (default: '1d'). Ignored if `start` is provided.
start : str, optional
    Start date in 'YYYY-MM-DD' format.
end : str, optional
    End date in 'YYYY-MM-DD' format.

Returns
-------
pandas.DataFrame
    Market data for the requested tickers and time range. Empty if no data
    is available.

Dependencies
------------
- yfinance
- pandas
- log_utils (for logging)
- contextlib, io (standard library)

Usage Example
-------------
    from data_fetch import get_market_data

    df = get_market_data(["AAPL", "MSFT"], interval="5m", period="1d")
    if not df.empty:
        print(df.tail())

Notes
-----
- Yahoo Finance may impose rate limits; excessive requests can result in
  temporary blocking.
- The returned DataFrame may be multi‑indexed if multiple tickers are
  requested.
"""

import yfinance as yf
import pandas as pd
from typing import List, Optional
import io
import contextlib
from log_utils import info, warn, error

def get_market_data(
    tickers: List[str],
    interval: str = "1m",
    period: Optional[str] = "1d",
    start: Optional[str] = None,
    end: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch market data for given tickers from Yahoo Finance.
    Suppresses raw Yahoo HTTP error output and replaces it with clean logs.
    """
    stderr_buffer = io.StringIO()
    with contextlib.redirect_stderr(stderr_buffer):
        try:
            df = yf.download(
                tickers=tickers,
                interval=interval,
                period=None if start else period,
                start=start,
                end=end,
                group_by='ticker',
                auto_adjust=True,
                threads=True,
                progress=False
            )
        except Exception as e:
            error(f"Failed to fetch data for {tickers}: {e}")
            return pd.DataFrame()

    raw_err = stderr_buffer.getvalue().strip()
    if raw_err:
        first_line = raw_err.splitlines()[0]
        warn(f"Yahoo Finance message for {tickers}: {first_line}")

    if df.empty:
        warn(f"No data returned for {tickers} (interval={interval}, period={period})")
        return pd.DataFrame()

    if isinstance(df.index, pd.DatetimeIndex):
        df.index = df.index.tz_localize(None)

    return df


