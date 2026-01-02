import streamlit as st
st.set_page_config(page_title="📊 TradeSentinel", layout="wide")
import pandas as pd
import numpy as np
from src.dashboard_core import (
    dynamic_filtering, load_tickers, confirm_unfollow_dialog,
    load_and_process_data
)
from src.analytics import calculate_portfolio
from src.dashboard_display import ( 
    display_credits, display_guides_section, display_info_section,
    display_period_selection, display_risk_return_plot
)
from src.config import EMA_PERIOD, followed_tickers_file

# ----------------------------------------------------------------------
# --- Data Helper Functions ---
# ----------------------------------------------------------------------

# Define columns for this dashboard
dist_EMA_column_name = f'dist_EMA_{EMA_PERIOD}'
DISPLAY_COLUMNS = ['Ticker', 'shortName', 'sector', 'beta', 'alpha', 'close', dist_EMA_column_name, 'forecastLow', 'forecastHigh', 'totalReturn', 'avgReturn', 'annualizedVol', 'sharpeRatio']

def _format_final_df(final_df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies rounding and ensures selected columns are present for display.
    """
    df = final_df.copy()

    # Ensure all DISPLAY_COLUMNS are present, filling missing with NaN
    for col in DISPLAY_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    
    # Explicitly ensure 'sector' column is a string type.
    if 'sector' in df.columns:
        df['sector'] = df['sector'].fillna('N/A').astype(str) 
    
    if "marketCap" in df.columns:
        df["marketCap"] = (df["marketCap"] / 1_000_000_000).round(2)  # 2 decimal places
        

    # Select only the display columns
    df = df[DISPLAY_COLUMNS]

    # Apply rounding
    for col in ['close', dist_EMA_column_name, 'beta', 'alpha', 'startPrice', 'forecastLow', 'forecastHigh', 'divPayout', 'totalReturn', 'avgReturn', 'annualizedVol', 'sharpeRatio']:
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
    sorted_df = final_df.sort_values(by='Ticker', ascending=True)

    # Apply dynamic filtering
    PAGE_KEY = "watchlist" # Unique ID for the main page

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
    event = st.dataframe(
        sorted_df,
        hide_index=True,
        width='stretch',
        on_select="rerun",
        selection_mode="multi-row", # allow multi-row selection
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "shortName": st.column_config.TextColumn("Short Name", width="medium"),
            "sector": st.column_config.TextColumn("sector"),
            "beta": st.column_config.NumberColumn("beta", help="Calculated beta for the lookback period", format="%.2f", width="small"),
            "alpha": st.column_config.NumberColumn("alpha", help="Calculated annualized alpha for the lookback period", format="%.2f%%", width="small"),
            "close": st.column_config.NumberColumn("price", help="Last Close price of the lookback period", format="$%.2f", width="small"),
            dist_EMA_column_name: st.column_config.NumberColumn(f"dist EMA {EMA_PERIOD}", help="Distance to the Exponential Moving Average (%)", format="%.2f%%", width="small"),        
            "forecastLow": st.column_config.NumberColumn("forecastLow", format="$%.2f", width="small"),
            "forecastHigh": st.column_config.NumberColumn("forecastHigh", format="$%.2f",width="small"),
            "totalReturn": st.column_config.NumberColumn("totalReturn", help="Total Return", format="%.2f%%", width="small"),                       
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

    # Followed tickers buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Backtest Portfolio", disabled=not selected_tickers):
            if selected_tickers:
                total_investment = 100000  # $100k initial investment
                
                # Pass the full daily data to the calculation function
                portfolio_tuples = calculate_portfolio(selected_tickers, df_daily, total_investment)
                st.session_state['portfolio'] = portfolio_tuples
                st.switch_page("pages/03_backtest.py")
            else:
                st.warning("Please select at least one ticker.")

        st.markdown("Select tickers to backtest a $100 k **equally-weighted portfolio**.")
    with col2:
        if st.button("Unfollow selected tickers", disabled=not selected_tickers):
            confirm_unfollow_dialog(selected_tickers)


# ----------------------------------------------------------------------
# --- Main Dashboard Function ---
# ----------------------------------------------------------------------

def main():
    st.title("📊 Watchlist")

    # User Input for Data Period
    current_fetch_kwargs = display_period_selection()

    # Check if reloading is needed
    should_reload = (
    'df_daily' not in st.session_state or
    'final_df_unformatted' not in st.session_state or 
    st.session_state.get('last_fetch_kwargs') != current_fetch_kwargs
    )
      
    # Retrieve Data (or Load if missing)
    if should_reload:
        # Load the FULL universe 
        with st.spinner('Loading Data...'):
            final_df_unformatted, df_daily, all_tickers = load_and_process_data(current_fetch_kwargs)
            
            # save to session state
            st.session_state['final_df_unformatted'] = final_df_unformatted
            st.session_state['df_daily'] = df_daily
            st.session_state['all_tickers'] = all_tickers
            st.session_state['last_fetch_kwargs'] = current_fetch_kwargs
            
    else:
        # Retrieve raw data
        final_df_unformatted = st.session_state['final_df_unformatted']
        df_daily = st.session_state['df_daily']
    
    # Apply formatting locally
    final_df = _format_final_df(final_df_unformatted)
    
    # Load the DF for the followed tickers
    followed_tickers_df = load_tickers(followed_tickers_file)
    followed_tickers = followed_tickers_df['Ticker'].tolist() if not followed_tickers_df.empty else []

    # Filter rows for tickers in watchlist
    watchlist_daily = df_daily[df_daily['Ticker'].isin(followed_tickers)].copy()
    watchlist_snapshot = final_df[final_df['Ticker'].isin(followed_tickers)].copy()
 
    if not watchlist_snapshot.empty:
        # Render the display sections if data is present        
        _render_summary_table_and_portfolio(watchlist_snapshot, watchlist_daily) # Pass watchlist_daily to the summary table function
    
    # Info section and guides in sidebar
    display_info_section(watchlist_daily)
    display_guides_section()
        
    # Credits & Navigation
    display_credits()
    if st.button("Go back to main page"):
        st.switch_page("main.py") 
    
if __name__ == "__main__":
    main()