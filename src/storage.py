import pandas as pd
from pathlib import Path
import streamlit as st
from src.config import DATA_DIR

def save_prices_incremental(ticker: str, interval: str, new_data: pd.DataFrame):
    """
    Save price data incrementally for a single ticker/interval,
    ensuring all columns are preserved and handling the index correctly.
    """
    interval_dir = DATA_DIR / "prices" / interval
    interval_dir.mkdir(parents=True, exist_ok=True)
    fp = interval_dir / f"{ticker.upper()}.parquet"

    df = new_data.copy()

    # Flatten the multi-level column DataFrame if it exists.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(1)

    # Ensure the index is a DatetimeIndex and has a name
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    
    # Set the index name to 'Date'
    df.index.name = "Date"
    df.dropna(subset=[df.index.name], inplace=True)
    
    # Add the 'Ticker' column to the new data
    df['Ticker'] = ticker

    # Merge with existing file if present
    if fp.exists():
        try:
            # Load old data and set 'Date' as the index for merging
            old = pd.read_parquet(fp).set_index("Date")
            old.index = pd.to_datetime(old.index)
            
            # Concatenate and handle duplicates, keeping the most recent data
            combined = pd.concat([old, df])
            combined = combined[~combined.index.duplicated(keep="last")]
            combined = combined.sort_index()
        except Exception as e:
            st.warning(f"Error reading {fp}: {e}. Overwriting file.")
            combined = df.sort_index()
    else:
        combined = df.sort_index()

    # Drop any columns that are all NaN
    combined = combined.dropna(axis=1, how='all')

    # Save the DataFrame with 'Date' as a regular column
    combined.reset_index(inplace=True)
    combined.to_parquet(fp)
    
    # The last date of the data is now in the 'Date' column
    if not combined.empty and "Date" in combined.columns:
        last_date = combined["Date"].max().date()
        










