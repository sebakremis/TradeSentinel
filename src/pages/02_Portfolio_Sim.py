# pages/02_Portfolio_Sim.py
import streamlit as st
import pandas as pd

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
    PERIOD_OPTIONS = ["1mo", "3mo", "6mo", "1y", "ytd", "max"]
    
    period_input = st.sidebar.selectbox(
        "Lookback Period", 
        PERIOD_OPTIONS, 
        index=PERIOD_OPTIONS.index("1y"), 
        key="active_period_input"
    )

    st.sidebar.markdown(f"**Interval:** `{FIXED_INTERVAL}` (Daily)")
    interval_input = FIXED_INTERVAL
    
    refresh = st.sidebar.button("Refresh Data")
    
    # 2. VALIDATION BLOCK (The Final Fix)
    if refresh:
        
        # Defensive Data Cleaning: Convert the entire DataFrame to strings first.
        # This prevents TypeErrors from unexpected Streamlit/Pandas types.
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
        # Coerce the string column to numeric, setting any non-numeric value (like 'nan', 'abc', or empty string) to NaN
        quantities_numeric = pd.to_numeric(clean_df["Quantity"], errors='coerce')

        invalid_quantities_found = False
        quantities_clean = []
        
        for q in quantities_numeric:
            # Check 1: Must be a valid number (i.e., not NaN after coercion)
            if pd.isna(q):
                invalid_quantities_found = True
                break
            
            # Check 2: Must be non-negative
            if q < 0:
                invalid_quantities_found = True
                break

            # Check 3: Must be a whole number (i.e., accept 100.0, reject 100.5)
            # Use a small tolerance for floating point comparison for robustness
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
        st.session_state.active_period = period_input
        st.session_state.active_interval = interval_input
        
        # Save the current valid portfolio
        clean_df['Quantity'] = quantities_clean
        st.session_state['portfolio'] = clean_df[['Ticker', 'Quantity']].values.tolist()

        # Clear cache and rerun
        try:
            # If your cache function is in scope, clear it
            _get_portfolio_data_cached.clear() 
        except NameError:
            pass # Ignore if not defined
        
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
    period = st.session_state.active_period
    interval = st.session_state.active_interval

    # 2. Load Data
    with st.spinner(f"Loading daily market data for {len(tickers)} tickers over {period}..."):
        prices = get_portfolio_data_cached(tickers, period=period, interval=interval)
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
        "🔗 [View Source Code on GitHub](https://github.com/sebakremis/TradeSentinel)",
        unsafe_allow_html=True
    )
    st.caption("Built using Streamlit and Python.")
    if st.button("Go back to Main Dashboard"):
        st.switch_page("main.py")

if __name__ == "__main__":
    main()