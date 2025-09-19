# src/data_fetch.py
import pandas as pd
import yfinance as yf
import io
import contextlib
import os

# Get the directory of the current script file (data_fetch.py)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Construct the absolute path to the CSV file
SECTOR_CSV_PATH = os.path.join(SCRIPT_DIR, "..", "data", "followed_tickers_sectors.csv")

def load_sector_data():
    """
    Loads sector data from a CSV file into a dictionary for fast lookup.
    """
    print(f"DEBUG: Attempting to load CSV from path: {SECTOR_CSV_PATH}")
    
    try:
        # Load the CSV without setting an index
        df = pd.read_csv(SECTOR_CSV_PATH)
        
        # Convert it to a dictionary for quick lookup
        sector_dict = df.set_index('Ticker')['Sector'].to_dict()
        
        print("DEBUG: CSV file loaded successfully.")
        print(f"DEBUG: Loaded sectors for tickers: {sector_dict.keys()}")
        return sector_dict
    except FileNotFoundError:
        print(f"❌ Error: The file was not found at {SECTOR_CSV_PATH}")
        return {}
    except Exception as e:
        print(f"❌ Error loading sector data from CSV: {e}")
        return {}

# Load the sector data once when the module is imported
SECTOR_DATA = load_sector_data()

def get_market_data(
    ticker: str,
    interval: str = "1d",
    period: str = "1y",
    start: str = None,
    end: str = None
) -> pd.DataFrame:
    """
    Fetch market data for a ticker from Yahoo Finance and adds sector data from a local CSV.
    """
    
    # Clean the ticker string to ensure a perfect match with the dictionary keys
    # .strip() removes whitespace, .upper() converts to uppercase
    clean_ticker = ticker.strip().upper()

    stderr_buffer = io.StringIO()
    with contextlib.redirect_stderr(stderr_buffer):
        try:
            ticker_obj = yf.Ticker(clean_ticker)
            df = ticker_obj.history(
                interval=interval,
                period=None if start else period,
                start=start,
                end=end,
                auto_adjust=True,
            )
        except Exception as e:
            print(f"❌ Failed to fetch {clean_ticker} ({period}, {interval}): {e}")
            return pd.DataFrame()

    if df.empty:
        print(f"⚠️ No data returned for {clean_ticker} ({period}, {interval})")
        return pd.DataFrame()

    if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    # Get sector from the pre-loaded dictionary using the clean ticker
    sector = SECTOR_DATA.get(clean_ticker, 'N/A')
    
    # Add the Ticker, Interval, and Sector columns to the DataFrame
    df["Ticker"] = clean_ticker
    df["Interval"] = interval
    df["Sector"] = sector
    
    return df



