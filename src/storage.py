from pathlib import Path
import pandas as pd
from src.config import BASE_DIR, DATA_DIR

def save_prices_incremental(ticker: str, interval: str, new_data: pd.DataFrame):
    """
    Save price data incrementally for a single ticker/interval,
    ensuring all columns are preserved.
    """
    # Use DATA_DIR to correctly construct the path to the prices directory
    interval_dir = DATA_DIR / "prices" / interval
    interval_dir.mkdir(parents=True, exist_ok=True)
    fp = interval_dir / f"{ticker.upper()}.parquet"

    df = new_data.copy()

    # Flatten MultiIndex columns if needed
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join([str(c) for c in col if c]) for col in df.columns]

    # Normalize column names
    # This is a safer and cleaner way to handle column renaming
    df.columns = df.columns.str.replace(f'{ticker.upper()}_', '', regex=False)
    
    # Ensure Date index
    if not isinstance(df.index, pd.DatetimeIndex):
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.set_index("Date")
    df.index.name = "Date"

    # Merge with existing file if present
    if fp.exists():
        try:
            old = pd.read_parquet(fp)
            old.index = pd.to_datetime(old.index)
            
            # Concatenate and handle duplicates
            combined = pd.concat([old, df])
            combined = combined[~combined.index.duplicated(keep="last")]
            combined = combined.sort_index()
        except Exception as e:
            # Handle potential corruption in old parquet files by overwriting
            print(f"Error reading {fp}: {e}. Overwriting file.")
            combined = df.sort_index()
    else:
        combined = df.sort_index()

    combined.to_parquet(fp)
    print(f"✅ Saved {ticker} {interval} up to {combined.index.max()}")






