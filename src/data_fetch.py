# src/data_fetch.py
import pandas as pd
import yfinance as yf
import io
import contextlib

# It's assumed that a logger object is defined elsewhere in your project,
# e.g., in a config or main module. For this example, we'll use a simple
# placeholder.
# If you have a logger, replace the print() statements with logger.error/warning.
# import logging
# logger = logging.getLogger(__name__)

def get_market_data(
    ticker: str,
    interval: str = "1d",
    period: str = "1y",
    start: str = None,
    end: str = None
) -> pd.DataFrame:
    """
    Fetch market data and company sector for a ticker from Yahoo Finance.
    
    This function uses yfinance to download historical price data and
    company information, then combines them into a single DataFrame.
    It also handles potential download errors and suppresses noisy output.
    """
    
    stderr_buffer = io.StringIO()
    with contextlib.redirect_stderr(stderr_buffer):
        try:
            # Create a Ticker object to fetch both price data and company info
            ticker_obj = yf.Ticker(ticker)
            
            # Fetch historical price data
            df = ticker_obj.history(
                interval=interval,
                period=None if start else period,
                start=start,
                end=end,
                auto_adjust=True,
            )            
            # Get the company's info dictionary
            info = ticker_obj.info
            
        except Exception as e:
            # Use your project's logger if available
            print(f"❌ Failed to fetch {ticker} ({period}, {interval}): {e}")
            return pd.DataFrame()

    if df.empty:
        # Use your project's logger if available
        print(f"⚠️ No data returned for {ticker} ({period}, {interval})")
        return pd.DataFrame()

    # If the index is a timezone-aware DatetimeIndex, make it timezone-naive
    if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    # Extract the 'sector' from the info dictionary and add it to the DataFrame
    # Use .get() to safely handle cases where the 'sector' key might be missing
    sector = info.get('sector', 'N/A')
    df["Sector"] = sector
    
    # Add the Ticker and Interval columns for easier data management
    df["Ticker"] = ticker
    df["Interval"] = interval
    
    return df



