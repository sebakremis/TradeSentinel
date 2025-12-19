import streamlit as st
st.set_page_config(page_title="📊 tradeSentinel", layout="wide")
import pandas as pd
import numpy as np
import altair as alt
import datetime 
from src.dashboard_manager import calculate_all_indicators, get_stock_data
from src.tickers_manager import load_tickers, confirm_follow_dialog, TickerValidationError
from src.dashboard_display import (
    highlight_change, display_credits, display_guides_section, display_info_section, display_period_selection
    )
from src.config import DATA_DIR, all_tickers_file
from src.etl import update_from_dashboard

# ----------------------------------------------------------------------
# --- Data Helper Functions ---
# ----------------------------------------------------------------------

DISPLAY_COLUMNS = ['Ticker', 'sector', 'marketCap', 'beta', 'close', '52WeekHigh', 'enterpriseToEbitda', 'priceToBook',  'dividendYield', 'returnOnAssets', 'avgReturn', 'annualizedVol', 'sharpeRatio']

def _format_final_df(final_df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies rounding and ensures selected columns are present for display.
    """
    df = final_df.copy()

    # Ensure all DISPLAY_COLUMNS are present, filling missing with NaN
    for col in DISPLAY_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    
    # Convert marketCap to billions and round   
    if "marketCap" in df.columns:
        df["marketCap"] = (df["marketCap"] / 1_000_000_000).round(2)  # 2 decimal places
    
    # Convert returnOnAssets to percentage
    if "returnOnAssets" in df.columns:
        df["returnOnAssets"] = (df["returnOnAssets"] * 100).round(2)  
        
    # Select only the display columns
    df = df[DISPLAY_COLUMNS]

    # Apply rounding
    for col in ['close', 'startPrice', 'divPayout', 'avgReturn', 'annualizedVol', 'sharpeRatio']:
        if col in df.columns:
            df[col] = df[col].round(2)           
    return df

def _load_and_process_data(fetch_kwargs: dict) -> (pd.DataFrame, pd.DataFrame, list): 
    # Load the DF for all tickers
    tickers_df = load_tickers(all_tickers_file)
    all_tickers = tickers_df['Ticker'].tolist() if not tickers_df.empty else []
    
    # load prices and metadata for all tickers
    df_daily = get_stock_data(
        all_tickers,
        interval="1d",
        **fetch_kwargs
    )

    if df_daily.empty:
        return pd.DataFrame(), pd.DataFrame(), all_tickers

    df_daily = calculate_all_indicators(df_daily)

    final_df_unformatted = df_daily.groupby('Ticker').tail(1).copy()

    start_prices = df_daily.groupby('Ticker')['close'].first().reset_index()
    start_prices.rename(columns={'close': 'startPrice'}, inplace=True)
    final_df_unformatted = final_df_unformatted.merge(start_prices, on='Ticker', how='left')

    final_df = _format_final_df(final_df_unformatted)

    return final_df, df_daily, all_tickers 

# ----------------------------------------------------------------------
# --- UI Rendering Functions ---
# ----------------------------------------------------------------------

def _render_summary_table_and_portfolio(final_df: pd.DataFrame, df_daily: pd.DataFrame):
    """Renders the summary table and portfolio simulation controls."""
    st.subheader("Summary")
   
    if final_df.empty:
        st.info("No data available to display in the summary table.")
        return

    sorted_df = final_df.sort_values(by='sharpeRatio', ascending=False)

    # Apply Conditional Formatting using Pandas Styler
    display_df_styled = sorted_df.copy()
    display_df_styled['Select'] = False # This must be done on the DataFrame copy before styling
    
    # Apply the color function to the 'avgReturn' column
    styled_table = display_df_styled.style.map(
        highlight_change, 
        subset=['avgReturn'] 
    )

    # --- Render Data Editor ---
    edited_df = st.data_editor(
        styled_table,
        hide_index=True,
        width='stretch',
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "sector": st.column_config.TextColumn("sector"),
            "marketCap": st.column_config.NumberColumn("marketCap", format="$%.1f B", width="small"),
            "beta": st.column_config.NumberColumn("beta", format="%.2f", width="small"),
            "close": st.column_config.NumberColumn("close", help="Last price of the lookback period", format="$%.2f", width="small"),
            "52WeekHigh": st.column_config.NumberColumn("52wHigh", help="52 Week High price", format="$%.2f", width="small"),
            "priceToBook": st.column_config.NumberColumn("priceToBook", help="Price to Book ratio", format="%.2f", width="small"),
            "enterpriseToEbitda": st.column_config.NumberColumn("enToEbitda", help="Enterprise value to EBITDA ratio", format="%.2f", width="small"),
            "dividendYield": st.column_config.NumberColumn("divYield", help="dividend yeld", format="%.2f%%",width="small"),
            "returnOnAssets": st.column_config.NumberColumn("ROA%", help="Return on Assets", format="%.2f%%",width="small"),                       
            "avgReturn": st.column_config.NumberColumn("AAR%", help="Annualized Average return", format="%.2f%%", width="small"),
            "annualizedVol": st.column_config.NumberColumn("Vol%", help="Annualized Average volatility", format="%.2f%%", width="small"),
            "sharpeRatio": st.column_config.NumberColumn("sharpe", format="%.2f%%", width="small"),                      
            "Select": st.column_config.CheckboxColumn("select", default=False, width="small")
        },
        num_rows="fixed"
    )
    
    selected_tickers_df = edited_df[edited_df['Select']]
    selected_tickers = selected_tickers_df['Ticker'].tolist()

    # Main dashboard buttons
    col1, col2 = st.columns([3, 1])
    with col1:
        pass
    with col2:
        if st.button("Follow Selected Tickers", disabled=not selected_tickers):
            confirm_follow_dialog(selected_tickers)

# ----------------------------------------------------------------------
# --- Main Dashboard Function ---
# ----------------------------------------------------------------------

def main():
    st.title("📊 tradeSentinel")
    st.markdown("---")

    # User Input for Data Period
    fetch_args = display_period_selection()
   
    # Load and process all data required for the main display
    # Pass the custom period/date argument
    final_df, df_daily, all_tickers = _load_and_process_data(fetch_kwargs=fetch_args)
  
    if not final_df.empty:
        # Render the summary table if data is present
        _render_summary_table_and_portfolio(final_df, df_daily) # Pass df_daily to the summary table function
    else:
        st.info("No data found.")
    
    # Update Database section
    st.markdown("---")
    st.subheader("Update Database")
    update_from_dashboard()  

    # Info section in sidebar
    display_info_section(df_daily)

    # Guides section in sidebar
    display_guides_section()

    # Credits
    display_credits()    

if __name__ == "__main__":
    main()