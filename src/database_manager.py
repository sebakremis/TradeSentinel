# src/database_manager.py
import sqlite3
import pandas as pd
import os
from log_utils import info, warn, error
from src.config import DATA_DIR

def init_db(db_name: str):
    """Initializes a new SQLite database if it doesn't exist."""
    db_path = f"{DATA_DIR}/{db_name}"
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            Ticker TEXT,
            Date TEXT,
            Time TEXT,
            Open REAL,
            High REAL,
            Low REAL,
            Close REAL,
            Volume INTEGER,
            PRIMARY KEY (Ticker, Date, Time)
        )
    """)
    conn.commit()
    conn.close()
    info(f"Database {db_path} initialized.")

def save_prices_to_db(df: pd.DataFrame, db_name: str):
    """Saves price data to the specified database."""
    db_path = f"{DATA_DIR}/{db_name}"
    conn = sqlite3.connect(db_path)
    df.to_sql("prices", conn, if_exists="replace", index=False)
    conn.close()
    info(f"Data saved to database {db_path}")

def load_prices_from_db(db_name: str) -> pd.DataFrame:
    """Loads all prices from the specified database."""
    db_path = f"{DATA_DIR}/{db_name}"
    if not os.path.exists(db_path):
        warn(f"Database file not found at {db_path}.")
        return pd.DataFrame()

    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM prices", conn)
        conn.close()

        if 'Time' in df.columns:
            df["Date"] = pd.to_datetime(df["Date"].astype(str) + " " + df["Time"].astype(str), errors='coerce')
            df.drop(columns=["Time"], inplace=True)
        else:
            df["Date"] = pd.to_datetime(df["Date"], errors='coerce')

        df.dropna(subset=['Date'], inplace=True)
        return df

    except Exception as e:
        error(f"Error loading data from database {db_name}: {e}")
        return pd.DataFrame()

def load_all_prices() -> pd.DataFrame:
    """Convenience function to load prices from the main dashboard database."""
    return load_prices_from_db("main_dashboard.db")