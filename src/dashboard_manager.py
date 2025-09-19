import pandas as pd
from pathlib import Path

# Assuming the root of your project is one level above src
from src.config import BASE_DIR, DATA_DIR

intervals_full = {
    "1m": "1 Minute",
    "2m": "2 Minutes",
    "5m": "5 Minutes",
    "15m": "15 Minutes",
    "30m": "30 Minutes",
    "60m": "60 Minutes",
    "90m": "90 Minutes",
    "1h": "1 Hour",
    "1d": "1 Day",
    "5d": "5 Days",
    "1wk": "1 Week",
    "1mo": "1 Month",
    "3mo": "3 Months"
}

intervals_main = {
    "1d": "1 Day",
    "30m": "30 Minutes"
}

def load_all_prices(interval, data_dir=DATA_DIR):
    """
    Loads all saved ticker price data for a given interval.
    """
    all_dfs = []
    
    # Construct the path to the directory containing the price data for the given interval
    interval_path = data_dir / "prices" / interval
    
    # --- DEBUGGING STATEMENTS ---
    print(f"Attempting to load data from: {interval_path}")
    if not interval_path.exists():
        print(f"Directory not found: {interval_path}")
        return pd.DataFrame()
    # --- END DEBUGGING STATEMENTS ---

    # Updated to look for .parquet files instead of .csv
    for file_path in interval_path.glob("*.parquet"):
        # --- DEBUGGING STATEMENTS ---
        print(f"Found file: {file_path}")
        # --- END DEBUGGING STATEMENTS ---
        try:
            df = pd.read_parquet(file_path)
            # Make sure the 'Ticker' column is correctly identified
            df['Ticker'] = file_path.stem
            all_dfs.append(df)
            # --- DEBUGGING STATEMENTS ---
            print(f"Successfully loaded file. DataFrame shape: {df.shape}")
            # --- END DEBUGGING STATEMENTS ---
        except Exception as e:
            # --- DEBUGGING STATEMENTS ---
            print(f"Error loading {file_path}: {e}")
            # --- END DEBUGGING STATEMENTS ---
            continue

    if not all_dfs:
        # --- DEBUGGING STATEMENTS ---
        print("No DataFrames were loaded for this interval.")
        # --- END DEBUGGING STATEMENTS ---
        return pd.DataFrame()

    # Fixed: Removed ignore_index=True to preserve the Date index
    combined_df = pd.concat(all_dfs)
    
    # --- DEBUGGING STATEMENTS ---
    print(f"Final combined DataFrame shape: {combined_df.shape}")
    print(f"Final combined DataFrame columns: {combined_df.columns.tolist()}")
    # --- END DEBUGGING STATEMENTS ---
    
    return combined_df










