import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from src.dashboard_display import display_period_selection
from src.dashboard_core import reload_data, load_tickers
from src.config import followed_tickers_file

st.set_page_config(page_title="📊 TradeSentinel", layout="wide")

# Define columns for this dashboard
DISPLAY_COLUMNS = ['Date', 'Ticker', 'shortName', 'open', 'high', 'low', 'close', 'volume']

def _format_df_daily(df_daily: pd.DataFrame) -> pd.DataFrame:
    """
    Applies rounding and ensures selected columns are present for display.
    """
    df = df_daily.copy()
    # Ensure all DISPLAY_COLUMNS are present, filling missing with NaN
    for col in DISPLAY_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
        
    # Select only the display columns
    df = df[DISPLAY_COLUMNS]

    # Apply rounding
    for col in ['open', 'high', 'low', 'close']:
        if col in df.columns:
            df[col] = df[col].round(2)           
    return df

def select_tickers(all_tickers: list, followed_tickers: list):
    """
    Render sidebar widgets to select a ticker.
    Uses a 'Source' selector to switch between Watchlist and All Tickers
    to avoid widget state conflicts.
    """
    with st.sidebar:
        st.header("Ticker Selection")
        
        # Select Source
        source = st.radio("Source:", ["Watchlist", "All Tickers"])
        
        # Define Options based on Source
        if source == "Watchlist":
            current_options = followed_tickers
            if not current_options:
                st.warning("Watchlist is empty.")
        else:
            current_options = all_tickers
            
        # Select Ticker
        selected_ticker = st.selectbox(
            "Select Ticker:", 
            options=current_options, 
            index= None
        )
        
    return selected_ticker

def main():
    st.title("📊 Charts")
    st.write("Under construction...")
    st.markdown("---")    

    # User Input for Data Period
    current_fetch_kwargs = display_period_selection()

    # Load data
    _ , df_daily_unformatted, all_tickers = reload_data(current_fetch_kwargs)

    # Apply formatting locally
    # df_daily_unformatted = df_daily_unformatted.reset_index()
    df_daily = _format_df_daily(df_daily_unformatted)

    # Load the list of followed tickers
    followed_tickers_df = load_tickers(followed_tickers_file)
    followed_tickers = followed_tickers_df['Ticker'].tolist() if not followed_tickers_df.empty else []

    # Sort lists
    all_tickers.sort()
    followed_tickers.sort()

    # Ticker selection sidebar
    current_ticker = select_tickers(all_tickers, followed_tickers)
    if not current_ticker:
        st.info("👈 Please select a ticker from the sidebar.")
        st.stop()

    # Chart Display
    st.header(f" {current_ticker}")
    ticker_data = df_daily[df_daily['Ticker'] == current_ticker].copy()   
    if not ticker_data.empty:
        st.write(f"Chart for {ticker_data['shortName'].iloc[0]}")
        # Sort by Date just in case
        ticker_data = ticker_data.sort_values("Date")

        fig = go.Figure(data=[go.Candlestick(
            x=ticker_data['Date'],
            open=ticker_data['open'],
            high=ticker_data['high'],
            low=ticker_data['low'],
            close=ticker_data['close']
        )])
        
        fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Price ($)',
            height=600,
            xaxis_rangeslider_visible=False # Optional: cleaner look without bottom slider
        )
        
        st.plotly_chart(fig, width='stretch')
    else:
        st.write(f"No data available for **{current_ticker}** in the specified period.")

if __name__ == "__main__":
    main()