# src/data_fetch.py
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


