# src/database_manager.py
import sqlite3
import pandas as pd
from src.config import DB_PATH # Import the correct path variable

def init_db():
    """Initializes the database and creates the 'prices' table if it doesn't exist."""
    # Ensure the data directory exists before trying to create the database file
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH) # Use the correct DB_PATH
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            Ticker TEXT,
            Date TEXT,
            Open REAL,
            High REAL,
            Low REAL,
            Close REAL,
            Volume INTEGER,
            PRIMARY KEY (Ticker, Date)
        )
    """)
    conn.commit()
    conn.close()

def save_prices_to_db(df: pd.DataFrame):
    """Saves a DataFrame of prices to the database."""
    conn = sqlite3.connect(DB_PATH)
    df.to_sql('prices', conn, if_exists='replace', index=False)
    conn.close()

def load_prices_from_db():
    """Loads all price data from the database into a DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM prices", conn)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index(['Date', 'Ticker'], inplace=True)
            return df
        return pd.DataFrame()
    except pd.io.sql.DatabaseError:
        return pd.DataFrame()
    finally:
        conn.close()