import streamlit as st
st.set_page_config(page_title="📊 TradeSentinel", layout="wide")
import pandas as pd
import numpy as np
from src.dashboard_core import dynamic_filtering, confirm_follow_dialog, load_and_process_data
from src.dashboard_display import (
    display_credits, display_guides_section, display_info_section, 
    display_period_selection, display_risk_return_plot
    )
from src.config import EMA_PERIOD
from src.etl import update_from_dashboard

# ----------------------------------------------------------------------
# --- Data Helper Functions ---
# ----------------------------------------------------------------------

# Define columns for this dashboard
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

# ----------------------------------------------------------------------
# --- UI Rendering Functions ---
# ----------------------------------------------------------------------

def _render_summary_table_and_portfolio(final_df: pd.DataFrame, df_daily: pd.DataFrame):
    """Renders the summary table and portfolio simulation controls."""
    if final_df.empty:
        st.info("No data available to display in the summary table.")
        return

    # sort data
    sorted_df = final_df.sort_values(by='alpha', ascending=False)

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
    current_fetch_kwargs = display_period_selection()

    # Check if reloading is needed
    should_reload = (
    'df_daily' not in st.session_state or 
    st.session_state.get('last_fetch_kwargs') != current_fetch_kwargs
    )
   
    # Load data
    if should_reload:
        with st.spinner('Loading Universe Data...'):
            final_df_unformatted, df_daily, all_tickers = load_and_process_data(current_fetch_kwargs)

            #Format final_df
            final_df = _format_final_df(final_df_unformatted)
            
            # Store in Session State
            st.session_state['final_df'] = final_df
            st.session_state['df_daily'] = df_daily
            st.session_state['all_tickers'] = all_tickers
            st.session_state['last_fetch_kwargs'] = current_fetch_kwargs
    else:
        # Retrieve from Session State
        final_df = st.session_state['final_df']
        df_daily = st.session_state['df_daily']
        all_tickers = st.session_state['all_tickers']
  
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