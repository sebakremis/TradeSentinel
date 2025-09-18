# src/data_fetch.py
import yfinance as yf
import pandas as pd
import contextlib, io
from loguru import logger

def get_market_data(
    ticker: str,
    interval: str = "1d",
    period: str = "1y",
    start: str = None,
    end: str = None
) -> pd.DataFrame:
    """
    Fetch market data for a ticker from Yahoo Finance.
    Ensures valid period/interval combos and suppresses noisy stderr.
    """
    stderr_buffer = io.StringIO()
    with contextlib.redirect_stderr(stderr_buffer):
        try:
            df = yf.download(
                tickers=ticker,
                interval=interval,
                period=None if start else period,
                start=start,
                end=end,
                group_by="ticker",
                auto_adjust=True,
                threads=True,
                progress=False,
            )
        except Exception as e:
            logger.error(f"❌ Failed to fetch {ticker} ({period}, {interval}): {e}")
            return pd.DataFrame()

    if df.empty:
        logger.warning(f"⚠️ No data returned for {ticker} ({period}, {interval})")
        return pd.DataFrame()

    if isinstance(df.index, pd.DatetimeIndex):
        df.index = df.index.tz_localize(None)

    df["Ticker"] = ticker
    df["Interval"] = interval
    return df



