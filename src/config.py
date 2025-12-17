# src/config.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

MAIN_DB_NAME = "main_dashboard.db"

# Define paths to new databases and folders
tickers_file = DATA_DIR / 'tickers_list.csv'
stocks_folder = DATA_DIR / 'stocks'
metadata_file = stocks_folder / 'metadata.csv'