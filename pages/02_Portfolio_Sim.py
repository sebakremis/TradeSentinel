import streamlit as st
import pandas as pd
import datetime # Import required for date inputs

from src.portfolio_calculations import calculate_pnl_data, prepare_pnl_time_series
from src.data_fetching import get_portfolio_data_cached
from src.dashboard_display import (
    display_per_ticker_pnl, display_portfolio_summary,
    display_pnl_over_time, display_sector_allocation,
    display_advanced_metrics, display_export_table
)
from src.database_manager import init_db

# --- Configuration and Initialization ---
DB_NAME = 'portfolio_data.db'
init_db(DB_NAME)

def _safe_df_concat(df1, df2):
    """Safely concatenates two DataFrames, handling Pandas append deprecation."""
    return pd.concat([df1, df2], ignore_index=True)

def setup_sidebar_controls():
    """Sets up the sidebar controls for portfolio definition and parameters, including validation."""
    
    # 1. Initialize DataFrame in Session State (Critical for clean start)
    if 'portfolio' not in st.session_state or st.session_state['portfolio'] is None:
        st.session_state['portfolio'] = []

    portfolio_tuples = st.session_state.get('portfolio')
    
    # Define a blank DataFrame structure. 'Int64' allows integer NA values.
    blank_df = pd.DataFrame(
        {'Ticker': pd.Series(dtype='str'), 'Quantity': pd.Series(dtype='Int64')}
    )

    if portfolio_tuples:
        # If data is present, load it, ensuring 'Quantity' is correctly typed
        sim_portfolio = pd.DataFrame(portfolio_tuples, columns=['Ticker', 'Quantity'])
        # Use pd.to_numeric to handle strings/floats, then use 'Int64' for nullable integers
        sim_portfolio['Quantity'] = pd.to_numeric(sim_portfolio['Quantity'], errors='coerce').fillna(0).astype('Int64')
    else:
        # Start with a single empty row to prompt user input
        new_row = pd.DataFrame([{'Ticker': '', 'Quantity': 0}])
        sim_portfolio = _safe_df_concat(blank_df, new_row)

    st.sidebar.title("Set portfolio to analyze:")
    
    # Use st.data_editor to allow users to modify the portfolio
    portfolio_df = st.sidebar.data_editor(
        sim_portfolio, 
        num_rows="dynamic", 
        width="stretch",
        # Use column config to enforce non-negative integers in the UI
        column_config={
            "Quantity": st.column_config.NumberColumn(
                "Quantity",
                help="Number of shares/units (non-negative integer)",
                min_value=0,
                step=1,
                format="%d"
            )
        }
    )

    # --- Fixed Parameters and Period Selection ---
    FIXED_INTERVAL = "1d"
    AVAILABLE_PERIODS = ["1mo", "3mo", "6mo", "ytd", "1y", "2y", "5y", "Custom Date"]

    # Get the period from the main dashboard's session state (initial/default)
    initial_period_arg = st.session_state.get('main_dashboard_period_arg', '1y') 
    
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
    
    refresh = st.sidebar.button("Refresh Data")
    
    # 2. VALIDATION BLOCK (The Final Fix)
    if refresh:
        
        # Defensive Data Cleaning: Convert the entire DataFrame to strings first.
        temp_df = portfolio_df.astype(str).copy()
        temp_df['Ticker'] = temp_df['Ticker'].str.strip()
        temp_df['Quantity'] = temp_df['Quantity'].str.strip()
        
        # Filter 1: Remove rows where the Ticker is empty
        clean_df = temp_df[temp_df['Ticker'] != ''].copy()
        
        # Filter 2: If the DataFrame is empty after filtering, stop processing gracefully
        if clean_df.empty:
            st.sidebar.warning("Please enter at least one ticker and quantity.")
            st.stop()

        tickers_input = clean_df["Ticker"].tolist()
        
        # Ticker Validation
        invalid_tickers = [t for t in tickers_input if not t or not t.replace('.', '').isalnum()]
        
        # Robust Quantity Conversion and Validation
        quantities_numeric = pd.to_numeric(clean_df["Quantity"], errors='coerce')

        invalid_quantities_found = False
        quantities_clean = []
        
        for q in quantities_numeric:
            # Check 1: Must be a valid number
            if pd.isna(q):
                invalid_quantities_found = True
                break
            
            # Check 2: Must be non-negative
            if q < 0:
                invalid_quantities_found = True
                break

            # Check 3: Must be a whole number 
            if abs(q - round(q)) < 1e-9: 
                quantities_clean.append(int(round(q))) 
            else:
                invalid_quantities_found = True
                break

        # Final Error Check
        if invalid_tickers or invalid_quantities_found:
            st.sidebar.error("Invalid input. Check tickers (must be alphanumeric/dot) and quantities (must be non-negative whole numbers).")
            st.stop()
        
        # Final commitment and rerun logic
        st.session_state.active_tickers = tickers_input
        st.session_state.active_quantities = dict(zip(tickers_input, quantities_clean))
        # 🚨 Use the dynamically calculated period_input
        st.session_state.active_period = period_input
        st.session_state.active_interval = interval_input
        
        # Save the current valid portfolio
        clean_df['Quantity'] = quantities_clean
        st.session_state['portfolio'] = clean_df[['Ticker', 'Quantity']].values.tolist()

        
        st.rerun()

# --- Main App Execution ---

def main():
    """The main function to run the Streamlit app content."""
    st.title("📈 Simulated Portfolio Analysis")
    
    # 1. Setup Sidebar and Control Flow
    setup_sidebar_controls()
    
    if "active_tickers" not in st.session_state:
        st.info("Set your portfolio parameters and click **Refresh Data** to load the dashboard.")
        st.stop()

    # Retrieve finalized parameters
    tickers = st.session_state.active_tickers
    quantities = st.session_state.active_quantities
    period_arg = st.session_state.active_period # Renamed to period_arg for clarity
    interval = st.session_state.active_interval

    # 🚨 FIX: Determine yfinance arguments based on the period_arg format
    fetch_kwargs = {'interval': interval}
    display_period = period_arg # Default display

    if '|' in period_arg:
        # Custom Date format found (e.g., '2025-09-10|2025-09-29')
        start_date, end_date = period_arg.split('|')
        fetch_kwargs['start'] = start_date
        fetch_kwargs['end'] = end_date
        # Display nicely for the user
        display_period = f"Custom: {start_date} to {end_date}"
    else:
        # Preset Period format (e.g., '1y')
        fetch_kwargs['period'] = period_arg
        display_period = period_arg

    # 2. Load Data
    with st.spinner(f"Loading daily market data for {len(tickers)} tickers over {display_period}..."):
        # 🚨 Pass the dynamically created arguments using the ** operator
        prices = get_portfolio_data_cached(tickers, **fetch_kwargs)
        st.session_state.data = prices
    
    if not prices:
        st.error("Could not load data for the selected portfolio. Please check tickers and try again.")
        st.stop()
        
    # 3. Calculate Core PnL Data
    df_pnl = calculate_pnl_data(prices, quantities)
    if df_pnl.empty:
        st.error("PnL calculation failed for all tickers.")
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
    st.markdown("---")
    st.markdown(
        "🔗 [View Source Code for original demo on GitHub](https://github.com/sebakremis/TradeSentinel)",
        unsafe_allow_html=True
    )
    st.markdown("👤 Developed by [Sebastian Kremis](mailto:skremis@ucm.es)")
    st.caption("Built using Streamlit and Python.")
    if st.button("Go back to Main Dashboard"):
        st.switch_page("main.py")

if __name__ == "__main__":
    main()