import pandas as pd
import streamlit as st
from pathlib import Path

# Assuming BASE_DIR is defined as a parent directory
from src.config import DATA_DIR, BASE_DIR

def load_followed_tickers(filename='followed_tickers_test.csv'):
    """
    Loads followed tickers from a single CSV file.
    Returns a DataFrame with 'Ticker' and 'Sector' columns.
    """
    # Construct the correct path to the tickers file using the DATA_DIR constant
    filepath = DATA_DIR / filename
    
    tickers_df = pd.DataFrame()

    try:
        tickers_df = pd.read_csv(filepath)
    except FileNotFoundError:
        st.error(f"❌ Error loading tickers: File not found at {filepath}")
        return pd.DataFrame(columns=['Ticker', 'Sector'])
    except Exception as e:
        st.error(f"❌ Error loading tickers: {e}")
        return pd.DataFrame(columns=['Ticker', 'Sector'])

    if tickers_df.empty or 'Ticker' not in tickers_df.columns:
        st.warning(f"⚠️ No tickers found in {filename} or 'Ticker' column is missing.")
        return pd.DataFrame(columns=['Ticker', 'Sector'])

    # Ensure 'Sector' column exists; add it if not found
    if 'Sector' not in tickers_df.columns:
        tickers_df['Sector'] = 'N/A'
        
    return tickers_df

def save_followed_tickers(tickers: list[str]) -> None:
    """Save tickers list to CSV."""
    ensure_data_dir()
    df = pd.DataFrame({"ticker": tickers})
    df.to_csv(TICKERS_FILE, index=False)

def add_ticker(ticker: str) -> None:
    """Add a ticker if not already present."""
    tickers = load_followed_tickers()
    if ticker not in tickers:
        tickers.append(ticker)
        save_followed_tickers(tickers)

def remove_ticker(ticker: str) -> None:
    """Remove a ticker if it exists."""
    tickers = load_followed_tickers()
    if ticker in tickers:
        tickers.remove(ticker)
        save_followed_tickers(tickers)
