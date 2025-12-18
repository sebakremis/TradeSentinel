# src/tickers_manager.py
from fileinput import filename
import pandas as pd
import streamlit as st
from pathlib import Path
import yfinance as yf
from src.config import tickers_file, DATA_DIR

# Define the path to the followed tickers CSV file
filepath = tickers_file
filename = filepath.name

# Define a custom exception for better error handling
class TickerValidationError(Exception):
    """Custom exception for invalid or missing ticker data."""
    pass

def load_followed_tickers():
    """
    Loads followed tickers from a single CSV file.
    Returns a DataFrame with a 'Ticker' column.
    """   
    
    tickers_df = pd.DataFrame()

    try:
        tickers_df = pd.read_csv(filepath)
    except FileNotFoundError:
        st.error(f"❌ Error loading tickers: File not found at {filepath}")
        return pd.DataFrame(columns=['Ticker'])
    except Exception as e:
        st.error(f"❌ Error loading tickers: {e}")
        return pd.DataFrame(columns=['Ticker'])

    if tickers_df.empty or 'Ticker' not in tickers_df.columns:
        st.warning(f"⚠️ No tickers found in {filename} or 'Ticker' column is missing.")
        return pd.DataFrame(columns=['Ticker'])
        
    return tickers_df

def save_followed_tickers(tickers: pd.DataFrame) -> None:
    """Save tickers list to CSV."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
        tickers.to_csv(filepath, index=False)
    except Exception as e:
        st.error(f"❌ Error saving tickers: {e}")
        return

def get_followed_tickers():
    """
    Manages the Streamlit session state for followed tickers.
    Returns the DataFrame.
    """
    try:
        followed_tickers_df = pd.read_csv(filepath)
    except FileNotFoundError:
        followed_tickers_df = pd.DataFrame(columns=['Ticker'])

    return followed_tickers_df

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
    if not info:
        raise TickerValidationError(f"Ticker '{ticker}' is not valid.")
         
    # Save the updated DataFrame to disk
    new_row = pd.DataFrame({'Ticker': [ticker]})
    expanded_df = pd.concat([tickers_df, new_row], ignore_index=True)
    save_followed_tickers(expanded_df)
    
def remove_ticker(ticker: str) -> None:
    """Removes a ticker if it is already present."""
    # Get the DataFrame from session state
    tickers_df = get_followed_tickers()
    
    # Check if the ticker exists in the list
    if ticker not in tickers_df['Ticker'].values:
        raise TickerValidationError(f"Ticker '{ticker}' is not currently being followed.")
    
    # Remove the ticker row using boolean indexing and update session state
    reduced_df = tickers_df[tickers_df['Ticker'] != ticker].reset_index(drop=True)
    
    # Save the updated DataFrame to disk
    save_followed_tickers(reduced_df)

@st.dialog("Confirm Unfollow")
def confirm_unfollow_dialog(tickers_to_remove:list):
    """
    Displays a confirmation dialog before unfollowing tickers.
    """
    st.write(f"Unfollowing tickers: **{', '.join(tickers_to_remove)}**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Confirm Unfollow"):
            for ticker in tickers_to_remove:
                try:
                    remove_ticker(ticker)
                except TickerValidationError as e:
                    st.error(f"❌ {e}")
            st.rerun()  # Refresh the app to reflect changes
    with col2:
        if st.button("Cancel"):
            st.rerun()  # Refresh the app to reflect changes