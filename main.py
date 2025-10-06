import streamlit as st
st.set_page_config(page_title="📊 TradeSentinel", layout="wide")
import pandas as pd
import numpy as np
import altair as alt
import datetime # Import required for custom date handling

# Import all necessary modules
from src.dashboard_manager import get_all_prices_cached, calculate_all_indicators
from src.tickers_manager import load_followed_tickers, add_ticker, remove_ticker, TickerValidationError
from src.sim_portfolio import calculate_portfolio
from src.dashboard_display import highlight_change
from src.indicators import annualized_risk_free_rate


# 🚨 ADDED 'Dividend' to the display columns
DISPLAY_COLUMNS = ['Ticker', 'Sector', 'Start Price', 'Close', 'Dividend', 'Highest Close', 'Lowest Close', 'Avg Return', 'Annualized Vol', 'Sharpe Ratio']

# ----------------------------------------------------------------------
# --- UI Callback Functions ---
# ----------------------------------------------------------------------

def handle_add_ticker_click():
    """Callback function to handle adding a new ticker symbol."""
    # Retrieve the ticker value from session state
    new_ticker = st.session_state.add_ticker_input.upper().strip()
        
    if not new_ticker:
        st.warning("Please enter a ticker symbol to add.")
        return 
        
    try:
        add_ticker(new_ticker) 
        st.session_state['add_ticker_input'] = ""
        st.success(f"✅ Added ticker {new_ticker}")
        st.rerun() 
            
    except TickerValidationError as e:
        st.error(f"❌ {e}")
        
    except Exception as e:
        st.error(f"❌ An unexpected error occurred: {e}")

# ----------------------------------------------------------------------
# --- Data Helper Functions ---
# ----------------------------------------------------------------------

def _format_final_df(final_df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies rounding and ensures selected columns are present for display.
    """
    df = final_df.copy()

    # 1. Ensure all DISPLAY_COLUMNS are present, filling missing with NaN
    for col in DISPLAY_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    
    # 2. CRITICAL FIX: Explicitly ensure 'Sector' column is a string type.
    if 'Sector' in df.columns:
        df['Sector'] = df['Sector'].fillna('N/A').astype(str) 

    # Select only the display columns
    df = df[DISPLAY_COLUMNS]

    # Apply rounding
    if 'Close' in df.columns:
        df['Close'] = df['Close'].round(2)
    if 'Start Price' in df.columns:
        df['Start Price'] = df['Start Price'].round(2)
    if 'Highest Close' in df.columns:
        df['Highest Close'] = df['Highest Close'].round(2)
    if 'Lowest Close' in df.columns:
        df['Lowest Close'] = df['Lowest Close'].round(2)
    if 'Dividend' in df.columns: 
        df['Dividend'] = df['Dividend'].round(2)
    
    # Rounding percentage/ratio columns
    for col in ['Avg Return', 'Annualized Vol', 'Sharpe Ratio']:
        if col in df.columns:
            df[col] = df[col].round(2)
            
    return df

def _load_and_process_data(PeriodOrStart= "1y") -> (pd.DataFrame, pd.DataFrame, list): 
    
    tickers_df = load_followed_tickers()
    followed_tickers = tickers_df['Ticker'].tolist() if not tickers_df.empty else []
    
    # Determine which argument to pass to the data fetcher
    fetch_kwargs = {}
    
    #  UPDATED LOGIC TO HANDLE START|END DATE STRING
    if '|' in PeriodOrStart:
        # Custom Start and End Dates were provided (e.g., '2024-01-01|2024-10-01')
        start_date, end_date = PeriodOrStart.split('|')
        fetch_kwargs['start'] = start_date
        fetch_kwargs['end'] = end_date # New argument for end date
        fetch_kwargs['period'] = None
        
    elif len(PeriodOrStart) > 5 and '-' in PeriodOrStart: 
        # Only a Custom Start Date was provided (if we had kept the previous logic)
        fetch_kwargs['start'] = PeriodOrStart
        fetch_kwargs['period'] = None
    else:
        # Preset Period String ('1y', '3mo', etc.)
        fetch_kwargs['period'] = PeriodOrStart
        fetch_kwargs['start'] = None
        
    # Add a cache-buster parameter based on the expected columns.
    # This forces Streamlit to re-run the cached function `get_all_prices_cached`
    # whenever the set of required display columns changes, preventing database schema conflicts.
    cache_version_key = len(DISPLAY_COLUMNS) 
        
    # Fetch data (assumes df_daily includes a 'Dividends' column if dividends were paid)
    df_daily = get_all_prices_cached(
        followed_tickers, 
        interval="1d",
        cache_version_key=cache_version_key, # NEW PARAMETER to invalidate cache
        **fetch_kwargs # Pass either 'period' or 'start' and 'end'
    )
    
    if df_daily.empty:
        return pd.DataFrame(), pd.DataFrame(), followed_tickers 

    # 1. Calculate indicators (operates on the full df_daily)
    df_daily = calculate_all_indicators(df_daily) 
    
    # 2. Get the latest snapshot (one row per ticker)
    final_df_unformatted = df_daily.groupby('Ticker').tail(1).copy()

    # 2A: Calculate Start Price for each Ticker
    start_prices = df_daily.groupby('Ticker')['Close'].first().reset_index()
    start_prices.rename(columns={'Close': 'Start Price'}, inplace=True)

    final_df_unformatted = final_df_unformatted.merge(
        start_prices, 
        on='Ticker', 
        how='left'
    )
    
    # 2B: Calculate Total Dividends for the Period
    if 'Dividends' in df_daily.columns:
        total_dividends = df_daily.groupby('Ticker')['Dividends'].sum().reset_index()
        total_dividends.rename(columns={'Dividends': 'Dividend'}, inplace=True)
        
        final_df_unformatted = final_df_unformatted.merge(
            total_dividends, 
            on='Ticker', 
            how='left'
        )
        final_df_unformatted['Dividend'] = final_df_unformatted['Dividend'].fillna(0)
    else:
        final_df_unformatted['Dividend'] = 0


    # Merge Sector information from the list of followed tickers
    if 'Sector' in tickers_df.columns and not final_df_unformatted.empty:
        # Merge the Sector column from tickers_df onto the snapshot DataFrame
        final_df_unformatted = final_df_unformatted.merge(
            tickers_df[['Ticker', 'Sector']], 
            on='Ticker', 
            how='left'
        )
        # Drop the potentially old/incorrect Sector column if it was generated by indicators
        if 'Sector_x' in final_df_unformatted.columns:
            final_df_unformatted['Sector'] = final_df_unformatted['Sector_y']
            final_df_unformatted.drop(columns=['Sector_x', 'Sector_y'], inplace=True)
    
    # 3. Format the data for display
    final_df = _format_final_df(final_df_unformatted)
    
    # Return both the snapshot (final_df) and the full daily data (df_daily)
    return final_df, df_daily, followed_tickers 


# ----------------------------------------------------------------------
# --- UI Rendering Functions ---
# ----------------------------------------------------------------------

def _render_overview_section(final_df: pd.DataFrame):
    """Renders the risk-return scatter plot."""
    st.subheader("Historical Risk-Return")

    if not final_df.empty and 'Avg Return' in final_df.columns and 'Annualized Vol' in final_df.columns:
        # Create the scatter plot using Altair
        chart = alt.Chart(final_df).mark_point(size=100).encode(
            x=alt.X('Annualized Vol', title='Annualized Volatility (Vol%)'),
            y=alt.Y('Avg Return', title='Annualized Average Return (AAR%)'),
            tooltip=['Ticker', 'Avg Return', 'Annualized Vol'],
            color=alt.Color('Ticker', legend=None)
        ).properties(
            title=''
        ).interactive()

        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("Cannot generate risk-return plot. Ensure tickers are selected and data is loaded.")


def _render_summary_table_and_portfolio(final_df: pd.DataFrame, df_daily: pd.DataFrame):
    """Renders the summary table and portfolio simulation controls."""
    st.subheader("Summary")

    
    if final_df.empty:
        st.info("No data available to display in the summary table.")
        return

    sorted_df = final_df.sort_values(by='Sharpe Ratio', ascending=False)

    # --- Apply Conditional Formatting using Pandas Styler ---
    display_df_styled = sorted_df.copy()
    display_df_styled['Select'] = False # This must be done on the DataFrame copy before styling
    
    # Apply the color function to the 'Avg Return' column
    styled_table = display_df_styled.style.map(
        highlight_change, 
        subset=['Avg Return'] 
    )


    edited_df = st.data_editor(
        styled_table,
        hide_index=True,
        width='stretch',
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Sector": st.column_config.TextColumn("Sector"),
            # "Change %": st.column_config.NumberColumn("Daily Chg%", format="%.2f%%"),
            # "Trading Days": st.column_config.NumberColumn("Days", help="Number of trading days in the selected lookback period.", width="small"),
            "Start Price": st.column_config.NumberColumn("First Price", format="$%.2f", width="small"),
            "Close": st.column_config.NumberColumn("Last Price", format="$%.2f", width="small"),
            "Dividend": st.column_config.NumberColumn("Div. Payout", help="Total dividends received during the lookback period.", format="$%.2f",width="small"),            
            "Highest Close": st.column_config.NumberColumn("Period High", format="$%.2f",width="small"),
            "Lowest Close": st.column_config.NumberColumn("Period Low", format="$%.2f", width="small"),           
            "Avg Return": st.column_config.NumberColumn("AAR%", format="%.2f%%", width="small"),
            "Annualized Vol": st.column_config.NumberColumn("Vol%", format="%.2f%%", width="small"),
            "Sharpe Ratio": st.column_config.NumberColumn("Sharpe", format="%.2f%%", width="small"),                      
            "Select": st.column_config.CheckboxColumn("Select", default=False, width="small")
        },
        disabled=['Change %'],
        num_rows="fixed"
    )
    
    selected_tickers_df = edited_df[edited_df['Select']]
    selected_tickers = selected_tickers_df['Ticker'].tolist()

    if st.button("Simulate Portfolio", disabled=not selected_tickers):
        if selected_tickers:
            total_investment = 100000
            # CRITICAL ADDITION: Save data required for the next page
            # Save the current period (already stored in session_state['main_dashboard_period_arg'])
            st.session_state['portfolio_period_arg'] = st.session_state['main_dashboard_period_arg']
            
            # Pass the full daily data to the calculation function
            portfolio_tuples = calculate_portfolio(selected_tickers, df_daily, total_investment)
            st.session_state['portfolio'] = portfolio_tuples
            st.switch_page("pages/02_Portfolio_Sim.py")
        else:
            st.warning("Please select at least one ticker.")

    st.markdown("Select tickers to simulate a $100 k **equally-weighted portfolio**.")


def _render_ticker_management_section(followed_tickers: list):
    """Renders the ticker list display and the add/remove controls."""
    st.markdown("---")
    st.subheader("Tickers Management")
    
    # 1. Display Followed Tickers
    st.markdown("**📝 Followed Tickers:**")
    if followed_tickers:
        num_cols = 5
        cols = st.columns(num_cols)
        
        for i, ticker in enumerate(followed_tickers):
            with cols[i % num_cols]:
                # Create a colorful badge for each ticker
                st.markdown(
                    f"<div style='background-color: #36454F; padding: 5px; border-radius: 5px; text-align: center; margin: 2px;'>"
                    f"<span style='color: #F5F5DC; font-weight: bold;'>{ticker}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
    else:
        st.info("No followed tickers. Please add tickers to follow.")
    
    # 2. Add/Remove Controls
    add_column, remove_column = st.columns(2)
    
    # Add Ticker Controls
    with add_column: 
        st.text_input("Enter Ticker Symbol to Add", max_chars=5, key='add_ticker_input')
        st.button(
            "Add Ticker", 
            key='add_button',
            on_click=handle_add_ticker_click
        )

    # Remove Ticker Controls
    with remove_column:
        rem_ticker_select = st.selectbox(
            "Select Ticker Symbol to Remove", 
            options=followed_tickers, # Use the list passed from load_followed_tickers
            key='rem_ticker_select'
        )
            
        if st.button("Remove Selected Ticker", key='remove_button'):
            if rem_ticker_select:
                try:
                    remove_ticker(rem_ticker_select)
                    st.success(f"✅ Removed ticker {rem_ticker_select}")
                except Exception as e:
                    st.error(f"❌ An error occurred while removing ticker: {e}")
            else:
                st.warning("Please select a ticker to remove.")
            st.rerun()

def render_info_section():
    st.sidebar.markdown("### ℹ️ Guides")
    
    with st.sidebar.expander("How calculations are made", expanded=False):
        st.subheader("Data Source & Lookback Period")
        st.markdown(
            """
            The data is sourced via an external financial data API (Yahoo Finance). 
            
            - **Data Type:** Daily Adjusted Closing Prices (`Close`), along with Sector and Dividend Payout.
            - **Caching:** Price data is **cached** (`@st.cache_data` within `get_all_prices_cached`) to improve performance and avoid excessive API calls. The cache is updated when the lookback period changes or the list of required columns is modified.
            """
        )

        st.subheader("Summary Table Column Methodology")
        
        st.markdown("**1. Close (Last Price)**")
        st.info("The latest Adjusted Close Price from the fetched data, rounded to 2 decimal places.")
        
        st.markdown("**2. Start Price**")
        st.info("The Adjusted Close Price on the **first day** of the selected Lookback Period. Used as the base for all period-related returns.")
        

        st.markdown("**3. Change %**")
        st.info("The percentage difference between the **Close Price** and the **Start Price**.")
        
        
        st.markdown("**4. Dividend (Div. Payout)**")
        st.info("The **Total Sum of Dividends** paid out per share for the stock over the entire Lookback Period.")
        

        st.markdown("**5. Highest Close / Lowest Close**")
        st.info("The highest/lowest Adjusted Close Price recorded during the Lookback Period.")
        
        st.markdown("**6. Avg Return (AAR%) / Annualized Vol (Vol%)**")
        st.info("These metrics are calculated using the daily logarithmic returns over the Lookback Period and are then **annualized** for comparison (assumes 252 trading days/year).")
        
        st.markdown("**7. Sharpe Ratio**")
        st.info("Calculated as the **Annualized Average Return** (AAR%) divided by the **Annualized Volatility** (Vol%). This is a key measure of risk-adjusted return (assumes a risk-free rate of 0% for simplicity in this demo).")
        

    with st.sidebar.expander("How to use the dashboard", expanded=False):
        st.markdown("""
        1. **Choose Lookback Period** for analysis (e.g., '1y' or 'Custom Date').
        2. **View Historical Risk-Return** chart for followed tickers.  
        3. **View Metrics summary** table.
        4. **Select Tickers** in the table and click **Simulate Portfolio** to analyze an equally-weighted $100k portfolio.
        5. **Manage Tickers**: Add or remove tickers to follow below.
        """)

# ----------------------------------------------------------------------
# --- Main Dashboard Function ---
# ----------------------------------------------------------------------

def main():
    st.set_page_config(layout="wide")
    st.title("📊 TradeSentinel-demo2")
    # Guide section in sidebar
    render_info_section()

    # --------------------------------------------------------------
    # User Input for Data Period (Revised Section for Start/End Date)
    # --------------------------------------------------------------
    
    # Define selectable periods (common Yahoo Finance periods)
    AVAILABLE_PERIODS = ["3mo", "6mo", "ytd", "1y", "2y", "5y", "Custom Date"]
    
    # 1. Period Selection
    selected_period = st.selectbox(
        "Lookback Period", 
        options=AVAILABLE_PERIODS, 
        index=AVAILABLE_PERIODS.index("1y"), # Default to 1 year
        key='data_period_select'
    )
    
    # Initialize the argument to be passed to the data fetcher
    period_arg = selected_period
    
    if selected_period == "Custom Date":
        
        # Define default values
        today = pd.Timestamp.now().normalize()
        default_start_date = today - pd.DateOffset(years=1)
        
        col1, col2 = st.columns(2)

        with col1:
            # 2a. Custom Start Date Selection
            custom_start_date = st.date_input(
                "Select Analysis **Start Date**", 
                value=default_start_date,
                max_value=today,
                key='custom_start_date_select'
            )
        
        with col2:
            # 2b. Custom End Date Selection (Default to Today)
            custom_end_date = st.date_input(
                "Select Analysis **End Date**", 
                value=today,
                min_value=custom_start_date, # End date cannot be before start date
                max_value=today,
                key='custom_end_date_select'
            )

        # CHANGE: Pack both dates into a tuple or list string to pass as the argument
        period_arg = f"{custom_start_date}|{custom_end_date}" 

    st.markdown("---") # Separator for cleaner UI
    
    # Load and process all data required for the main display
    # Pass the custom period/date argument
    final_df, df_daily, followed_tickers = _load_and_process_data(PeriodOrStart=period_arg)
  
    # Save the period_arg into the session state
    st.session_state['main_dashboard_period_arg'] = period_arg 

    # New Info section
    if not df_daily.empty and 'Date' in df_daily.columns:
        num_days = df_daily['Date'].nunique()
        first_date = pd.to_datetime(df_daily['Date'].min())
        last_date = pd.to_datetime(df_daily['Date'].max())
    else:
        num_days = 0
        first_date, last_date = None, None

    with st.expander("ℹ️ Trading Period Info", expanded=False):
        st.write(f"**Trading Days:** {num_days}")
        st.write(f"**First Price Date:** {first_date.strftime('%Y-%m-%d') if first_date else 'N/A'}")
        st.write(f"**Last Price Date:** {last_date.strftime('%Y-%m-%d') if last_date else 'N/A'}")
        st.write(f"**Annualized Risk Free rate:** {annualized_risk_free_rate*100:.2f}% (assumed risk-free rate for Sharpe Ratio calculation)")


    if not final_df.empty:
        # Render the display sections if data is present
        _render_overview_section(final_df)
        _render_summary_table_and_portfolio(final_df, df_daily) # Pass df_daily to the summary table function
    else:
        st.info("No data found. Add a ticker using the management controls below and click 'Update Prices' to fetch data.")
        
    # Tickers management and Update Prices are always visible
    _render_ticker_management_section(followed_tickers)
    
    # Credits
    st.markdown("---")
    st.markdown(
        "🔗 [View Source Code for demo1 (legacy version) on GitHub](https://github.com/sebakremis/TradeSentinel-demo1)",
        unsafe_allow_html=True
    )
    st.markdown("👤 Developed by [Sebastian Kremis](mailto:skremis@ucm.es)")
    st.caption("Built using Streamlit and Python.")
    
    

if __name__ == "__main__":
    main()