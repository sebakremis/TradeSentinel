# src/tickers_manager.py
import pandas as pd
import streamlit as st
from pathlib import Path
import yfinance as yf

# Assuming BASE_DIR is defined as a parent directory
from src.config import DATA_DIR, BASE_DIR

# Define a custom exception for better error handling
class TickerValidationError(Exception):
    """Custom exception for invalid or missing ticker data."""
    pass

def load_followed_tickers(filename='followed_tickers.csv'):
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

def save_followed_tickers(tickers: pd.DataFrame) -> None:
    """Save tickers list to CSV."""
    TICKERS_FILE = DATA_DIR / 'followed_tickers.csv'
    try:
        TICKERS_FILE.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
        tickers.to_csv(TICKERS_FILE, index=False)
    except Exception as e:
        st.error(f"❌ Error saving tickers: {e}")
        return

def get_followed_tickers():
    """
    Manages the Streamlit session state for followed tickers.
    Initializes the state if it doesn't exist and returns the DataFrame.
    """
    if 'followed_tickers_df' not in st.session_state:
        # Load from file only the first time
        filepath = DATA_DIR / 'followed_tickers.csv'
        try:
            st.session_state.followed_tickers_df = pd.read_csv(filepath)
            # Ensure 'Sector' column exists
            if 'Sector' not in st.session_state.followed_tickers_df.columns:
                st.session_state.followed_tickers_df['Sector'] = 'N/A'
        except FileNotFoundError:
            st.session_state.followed_tickers_df = pd.DataFrame(columns=['Ticker', 'Sector'])
    
    return st.session_state.followed_tickers_df

def add_ticker(ticker: str) -> None:
    """Add a ticker after fetching and validating its sector."""
    # Get the DataFrame from session state
    tickers_df = get_followed_tickers()
    
    # Check for duplicates
    if ticker in tickers_df['Ticker'].values:
        raise TickerValidationError(f"Ticker '{ticker}' is already being followed.")
    
    # Fetch data from Yahoo Finance
    yf_ticker = yf.Ticker(ticker)
    info = yf_ticker.info

    # Validate the ticker
    if not info or 'sector' not in info:
        raise TickerValidationError(f"Ticker '{ticker}' is not valid or no sector information could be found.")
    
    sector = info.get('sector', 'N/A')
    new_row = pd.DataFrame({"Ticker": [ticker], "Sector": [sector]})
    
    # Update the session state DataFrame directly
    st.session_state.followed_tickers_df = pd.concat([tickers_df, new_row], ignore_index=True)
    
    # Save the updated DataFrame to disk
    save_followed_tickers(st.session_state.followed_tickers_df)
    
def remove_ticker(ticker: str) -> None:
    """Removes a ticker if it is already present."""
    # Get the DataFrame from session state
    tickers_df = get_followed_tickers()
    
    # Check if the ticker exists in the list
    if ticker not in tickers_df['Ticker'].values:
        raise TickerValidationError(f"Ticker '{ticker}' is not currently being followed.")
    
    # Remove the ticker row using boolean indexing and update session state
    st.session_state.followed_tickers_df = tickers_df[tickers_df['Ticker'] != ticker]
    
    # Save the updated DataFrame to disk
    save_followed_tickers(st.session_state.followed_tickers_df)