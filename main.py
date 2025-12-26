import streamlit as st
st.set_page_config(page_title="📊 TradeSentinel", layout="wide")
import pandas as pd
import numpy as np
import altair as alt
import datetime 
from src.dashboard_core import (
    calculate_all_indicators, get_stock_data, dynamic_filtering,
    load_tickers, confirm_follow_dialog, TickerValidationError
)
from src.dashboard_display import (
    display_credits, display_guides_section, display_info_section, 
    display_period_selection, display_risk_return_plot
    )
from src.config import DATA_DIR, all_tickers_file, EMA_PERIOD
from src.etl import update_from_dashboard

# ----------------------------------------------------------------------
# --- Data Helper Functions ---
# ----------------------------------------------------------------------
dist_EMA_column_name = f'dist_EMA_{EMA_PERIOD}'
DISPLAY_COLUMNS = ['Ticker', 'shortName', 'sector', 'marketCap', 'beta', 'alpha', 'close', dist_EMA_column_name, 'enterpriseToEbitda', 'priceToBook', 'avgReturn', 'annualizedVol', 'sharpeRatio']

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
    for col in ['close', dist_EMA_column_name, 'startPrice', 'divPayout', 'avgReturn', 'annualizedVol', 'sharpeRatio']:
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
    if final_df.empty:
        st.info("No data available to display in the summary table.")
        return

    # sort data
    sorted_df = final_df.sort_values(by='avgReturn', ascending=False)

    # Apply dynamic filtering
    PAGE_KEY = "main" # Unique ID for the main page

    # Initialize THIS page's counter
    if f'{PAGE_KEY}_filter_count' not in st.session_state:
        st.session_state[f'{PAGE_KEY}_filter_count'] = 1

    # Loop using THIS page's counter
    for i in range(st.session_state[f'{PAGE_KEY}_filter_count']):
        sorted_df = dynamic_filtering(sorted_df, DISPLAY_COLUMNS, i, key_prefix=PAGE_KEY)

    # --- Risk-Return Plot ---
    display_risk_return_plot(sorted_df)

    # Show active row count 
    if len(sorted_df) != len(final_df):
        st.caption(f"Showing {len(sorted_df)} of {len(final_df)} tickers based on filter.")
    else:
        st.caption(f"Showing all {len(final_df)} tickers.")

    # --- Render Dataframe table ---    
    event = st.dataframe( # Capture the 'event' to know which rows are selected
        sorted_df,
        hide_index=True,
        width='stretch',
        on_select="rerun",
        selection_mode="multi-row", # allow multi-row selection
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "shortName": st.column_config.TextColumn("Short Name", width="medium"),
            "sector": st.column_config.TextColumn("sector"),
            "marketCap": st.column_config.NumberColumn("marketCap", format="$%.1f B", width="small"),
            "beta": st.column_config.NumberColumn("beta", help="Calculated beta for the lookback period", format="%.2f", width="small"),
            "alpha": st.column_config.NumberColumn("alpha", help="Calculated alpha for the lookback period", format="%.2f", width="small"),
            "close": st.column_config.NumberColumn("price", help="Last Close price of the lookback period", format="$%.2f", width="small"),
            dist_EMA_column_name: st.column_config.NumberColumn(f"dist EMA {EMA_PERIOD}", help="Distance to the Exponential Moving Average (%)", format="%.2f%%", width="small"),
            "priceToBook": st.column_config.NumberColumn("priceToBook", help="Price to Book ratio", format="%.2f", width="small"),
            "enterpriseToEbitda": st.column_config.NumberColumn("enToEbitda", help="Enterprise value to EBITDA ratio", format="%.2f", width="small"),                     
            "avgReturn": st.column_config.NumberColumn("AAR%", help="Annualized Average return", format="%.2f%%", width="small"),
            "annualizedVol": st.column_config.NumberColumn("Vol%", help="Annualized Average volatility", format="%.2f%%", width="small"),
            "sharpeRatio": st.column_config.NumberColumn("sharpe", format="%.2f%%", width="small")
        },
    )
    # Get tickers from selected rows.
    selected_indices = event.selection.rows # returns a list of numerical indices
    selected_tickers_df = sorted_df.iloc[selected_indices]

    # Get list of selected tickers
    selected_tickers = selected_tickers_df['Ticker'].tolist()

    # Main dashboard buttons
    if st.button("Add to watchlist", disabled=not selected_tickers):
        confirm_follow_dialog(selected_tickers)

# ----------------------------------------------------------------------
# --- Main Dashboard Function ---
# ----------------------------------------------------------------------

def main():
    st.title("📊 TradeSentinel")
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