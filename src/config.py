# src/config.py
from pathlib import Path

# Define base directory and data directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Define path to tickers CSV files
followed_tickers_file = DATA_DIR / 'followed_tickers.csv'
all_tickers_file = DATA_DIR / 'all_tickers.csv'

# Define paths to database and folders
stocks_folder = DATA_DIR / 'stocks'
metadata_file = stocks_folder / 'metadata.csv'