import streamlit as st
st.set_page_config(page_title="📊 TradeSentinel", layout="wide")
import pandas as pd

from src.analytics import calculate_pnl_data, prepare_pnl_time_series
from src.dashboard_core import get_stock_data
from src.dashboard_display import (
    display_per_ticker_pnl, display_portfolio_summary,
    display_pnl_over_time, display_sector_allocation,
    display_advanced_metrics, display_export_table, display_credits,
    display_guides_section, display_period_selection, display_guides_section,
    display_info_section
)
from src.config import DEFAULT_LOOKBACK_PERIOD, FIXED_INTERVAL

def setup_sidebar_controls():
    """Sets up the sidebar controls for portfolio definition and parameters, including validation."""
    
    # 1. Initialize DataFrame in Session State
    if 'portfolio' not in st.session_state or st.session_state['portfolio'] is None:
        st.session_state['portfolio'] = []

    portfolio_data = st.session_state.get('portfolio')
    
    # Define schema using specific types
    df_schema = {'Ticker': pd.Series(dtype='str'), 'Quantity': pd.Series(dtype='Int64')}

    if portfolio_data:
        # Load existing data
        sim_portfolio = pd.DataFrame(portfolio_data, columns=['Ticker', 'Quantity'])
        # Ensure Quantity is numeric and nullable Int64
        sim_portfolio['Quantity'] = pd.to_numeric(sim_portfolio['Quantity'], errors='coerce').astype('Int64')
    else:
        # Initialize empty DataFrame. 'dynamic' mode in data_editor handles adding rows.
        sim_portfolio = pd.DataFrame(df_schema)

    st.sidebar.title("Set portfolio to analyze:")
    
    # Using data_editor with num_rows="dynamic" removes need for manual blank row insertion
    portfolio_df = st.sidebar.data_editor(
        sim_portfolio, 
        num_rows="dynamic", 
        width="stretch",
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", required=True),
            "Quantity": st.column_config.NumberColumn(
                "Quantity",
                help="Number of shares/units (non-negative integer)",
                min_value=0, # UI restriction
                step=1,
                format="%d",
                required=True
            )
        },
        key="portfolio_editor"
    )

    # Period selection
    current_fetch_kwargs = display_period_selection()
       
    # VALIDATION & REFRESH LOGIC
    if st.sidebar.button("Refresh Data", type="primary"):
        
        # Clean Inputs
        clean_df = portfolio_df.copy()
        
        # Drop rows where Ticker is missing or NaN
        clean_df = clean_df.dropna(subset=['Ticker'])
        clean_df = clean_df[clean_df['Ticker'].astype(str).str.strip() != '']
        
        if clean_df.empty:
            st.sidebar.warning("Please enter at least one ticker.")
            st.stop()

        # Vectorized Validation
        # 1. Ticker Validation (alphanumeric check)
        # We strip strings and remove dots/periods before checking isalnum
        invalid_tickers_mask = ~clean_df['Ticker'].astype(str).str.replace('.', '', regex=False).str.isalnum()
        
        # 2. Quantity Validation
        # Coerce to numeric, anything that fails becomes NaN
        clean_df['Quantity'] = pd.to_numeric(clean_df['Quantity'], errors='coerce')
        invalid_qty_mask = clean_df['Quantity'].isna() | (clean_df['Quantity'] < 0)

        if invalid_tickers_mask.any() or invalid_qty_mask.any():
            st.sidebar.error("Invalid input detected. Check Tickers (alphanumeric) and Quantities (positive numbers).")
            st.stop()

        # Prepare Final Data
        clean_df['Ticker'] = clean_df['Ticker'].astype(str).str.upper().str.strip()
        clean_df['Quantity'] = clean_df['Quantity'].astype(int)

        # Commit to Session State
        tickers_input = clean_df["Ticker"].tolist()
        quantities_clean = clean_df["Quantity"].tolist()
        
        st.session_state.active_tickers = tickers_input
        st.session_state.active_quantities = dict(zip(tickers_input, quantities_clean))

        # Save the fetch kwargs
        st.session_state.active_fetch_kwargs = current_fetch_kwargs
        st.session_state.active_interval = FIXED_INTERVAL
        
        # Save portfolio for persistence (as list of lists/tuples for simplicity)
        st.session_state['portfolio'] = clean_df[['Ticker', 'Quantity']].values.tolist()
        
        st.rerun()

# --- Main App Execution ---

def main():
    """The main function to run the Streamlit app content."""
    st.title("📈 Backtest")
    
    # 1. Setup Sidebar and Control Flow
    setup_sidebar_controls()
    
    if "active_tickers" not in st.session_state:
        st.info("👈 Set your portfolio parameters and click **Refresh Data** to load the dashboard.")
        st.stop()

    # Retrieve parameters
    tickers = st.session_state.active_tickers
    quantities = st.session_state.active_quantities
    fetch_kwargs = st.session_state.get('active_fetch_kwargs', {'period': DEFAULT_LOOKBACK_PERIOD})

    # Label for the spinner
    if fetch_kwargs.get('period'):
        display_period_label = fetch_kwargs['period']
    else:
        display_period_label = f"Custom: {fetch_kwargs.get('start')} to {fetch_kwargs.get('end')}"

    # Load Data
    with st.spinner(f"Loading data for {len(tickers)} tickers ({display_period_label})..."):
        prices_df = get_stock_data(tickers, **fetch_kwargs)
        
        if prices_df.empty:
            st.error("No data returned. Please check your tickers or date range.")
            st.stop()
            
        prices_df.set_index('Date', inplace=True)
        prices_df.sort_index(inplace=True)

        # OPTIMIZATION: Use groupby instead of list comprehension for speed
        # This splits the big dataframe into a dict of small dataframes in one go
        prices = dict(tuple(prices_df.groupby('Ticker')))
        
        # Handle cases where a ticker might have returned no data despite request
        missing_tickers = set(tickers) - set(prices.keys())
        if missing_tickers:
            st.warning(f"Could not load data for: {', '.join(missing_tickers)}")
            # Filter quantities to match available data to prevent KeyErrors later
            quantities = {k: v for k, v in quantities.items() if k not in missing_tickers}

    # Calculate Core PnL Data
    df_pnl = calculate_pnl_data(prices, quantities)
    
    if df_pnl.empty:
        st.error("PnL calculation yielded no results.")
        st.stop()

    # --- Display Sections ---

    display_per_ticker_pnl(df_pnl)
    st.markdown("---")

    display_portfolio_summary(df_pnl)
    st.markdown("---")

    combined_df = prepare_pnl_time_series(prices, quantities)

    display_pnl_over_time(combined_df)
    st.markdown("---")

    display_sector_allocation(df_pnl)
    st.markdown("---")

    display_advanced_metrics(combined_df)
    st.markdown("---")

    display_export_table(combined_df)

    # Guides section in sidebar
    display_info_section(prices_df.reset_index())
    display_guides_section()

    # Credits and Navigation
    display_credits()
    if st.button("Go back to main page"):
        st.switch_page("main.py")

if __name__ == "__main__":
    main()