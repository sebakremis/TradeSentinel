import streamlit as st
st.set_page_config(page_title="📊 TradeSentinel", layout="wide")
import pandas as pd

from src.analytics import calculate_pnl_data, prepare_pnl_time_series
from src.dashboard_core import get_stock_data
from src.dashboard_display import (
    display_per_ticker_pnl, display_portfolio_summary,
    display_pnl_over_time, display_sector_allocation,
    display_advanced_metrics, display_export_table, display_credits,
    display_guides_section
)


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

    # --- Fixed Parameters and Period Selection ---
    FIXED_INTERVAL = "1d"
    AVAILABLE_PERIODS = ["3mo", "6mo", "ytd", "1y", "2y", "5y", "Custom Date"]

    # Get the period from the main dashboard's session state (initial/default)
    initial_period_arg = '2y'
    
    # Determine which value should be selected by default in the selectbox
    if '|' in initial_period_arg:
        default_select_value = "Custom Date"
    elif initial_period_arg in AVAILABLE_PERIODS:
        default_select_value = initial_period_arg
    else:
        default_select_value = "1y" # Final fallback

    # st.sidebar.subheader("Lookback Period")
    
    # Selectbox allows overriding the period passed from the main dashboard
    selected_override = st.sidebar.selectbox(
        "Lookback period", 
        options=AVAILABLE_PERIODS, 
        index=AVAILABLE_PERIODS.index(default_select_value),
        key='portfolio_period_override_select'
    )

    period_input = selected_override # Start with the selected value
    
    # Handle Custom Date Selection
    if selected_override == "Custom Date":
        today = pd.Timestamp.now().normalize().date()
        
        # Initialize default dates for the custom picker based on initial_period_arg
        default_end_date = today
        default_start_date = today - pd.DateOffset(years=1)
        
        if '|' in initial_period_arg:
            try:
                # Try to use the date range passed from main.py as the default
                default_start_str, default_end_str = initial_period_arg.split('|')
                default_start_date = pd.to_datetime(default_start_str).date()
                default_end_date = pd.to_datetime(default_end_str).date()
            except Exception:
                # If parsing fails, stick to 1-year default
                pass

        custom_start_date = st.sidebar.date_input(
            "Start Date", 
            value=default_start_date,
            max_value=default_end_date,
            key='custom_start_date_sim'
        )
        
        custom_end_date = st.sidebar.date_input(
            "End Date", 
            value=default_end_date,
            min_value=custom_start_date, 
            max_value=today,
            key='custom_end_date_sim'
        )

        # Set the period_input to the custom date string format
        period_input = f"{custom_start_date}|{custom_end_date}"

    # Display the final period argument being used
    if '|' in period_input:
        start_date, end_date = period_input.split('|')
        display_period = f"Custom: {start_date} to {end_date}"
    else:
        display_period = period_input

    
    st.sidebar.markdown(f"**Fixed Interval:** `{FIXED_INTERVAL}`")
    interval_input = FIXED_INTERVAL
       
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
        st.session_state.active_period = period_input
        st.session_state.active_interval = FIXED_INTERVAL
        
        # Save portfolio for persistence (as list of lists/tuples for simplicity)
        st.session_state['portfolio'] = clean_df[['Ticker', 'Quantity']].values.tolist()
        
        st.rerun()
    
    # Guides on sidebar
    display_guides_section()

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
    period_arg = st.session_state.active_period
    interval = st.session_state.active_interval

    # Configure fetch arguments
    fetch_kwargs = {'interval': interval}
    display_period_label = period_arg

    if '|' in period_arg:
        start_date, end_date = period_arg.split('|')
        fetch_kwargs['start'] = start_date
        fetch_kwargs['end'] = end_date
        display_period_label = f"Custom: {start_date} to {end_date}"
    else:
        fetch_kwargs['period'] = period_arg

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

    # Credits and Navigation
    display_credits()
    if st.button("Go back to main page"):
        st.switch_page("main.py")

if __name__ == "__main__":
    main()