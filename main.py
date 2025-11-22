import streamlit as st
st.set_page_config(page_title="📊 TradeSentinel", layout="wide")
import pandas as pd
import numpy as np
import altair as alt
import datetime 

# Import all necessary modules
from src.dashboard_manager import get_all_prices_cached, calculate_all_indicators
from src.tickers_manager import load_followed_tickers, add_ticker, remove_ticker, TickerValidationError
from src.sim_portfolio import calculate_portfolio
from src.dashboard_display import highlight_change
from src.indicators import annualized_risk_free_rate
from src.price_forecast import project_price_range

DISPLAY_COLUMNS = ['Ticker', 'Sector', 'MarketCap', 'Beta', 'Start Price', 'Close', 'Dividend',  'Forecast Low', 'Forecast High', 'Avg Return', 'Annualized Vol', 'Sharpe Ratio']

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

    # Ensure all DISPLAY_COLUMNS are present, filling missing with NaN
    for col in DISPLAY_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    
    # Explicitly ensure 'Sector' column is a string type.
    if 'Sector' in df.columns:
        df['Sector'] = df['Sector'].fillna('N/A').astype(str) 
    
    if "MarketCap" in df.columns:
        df["MarketCap"] = (df["MarketCap"] / 1_000_000_000).round(2)  # 2 decimal places
        

    # Select only the display columns
    df = df[DISPLAY_COLUMNS]

    # Apply rounding
    for col in ['Close', 'Start Price', 'Forecast Low', 'Forecast High', 'Dividend', 'Avg Return', 'Annualized Vol', 'Sharpe Ratio']:
        if col in df.columns:
            df[col] = df[col].round(2)
            
    return df


@st.cache_data
def _cached_forecast(df_snapshot: pd.DataFrame) -> pd.DataFrame:
    return project_price_range(
        df_snapshot[['Ticker', 'Close', 'Avg Return', 'Annualized Vol']].drop_duplicates(subset=['Ticker']),
        period_months=1,
        n_sims=10000
    )

def _load_and_process_data(PeriodOrStart= "1y") -> (pd.DataFrame, pd.DataFrame, list): 
    
    tickers_df = load_followed_tickers()
    followed_tickers = tickers_df['Ticker'].tolist() if not tickers_df.empty else []

    fetch_kwargs = {}

    if '|' in PeriodOrStart:
        start_date, end_date = PeriodOrStart.split('|')
        fetch_kwargs['start'] = start_date
        fetch_kwargs['end'] = end_date
        fetch_kwargs['period'] = None
    elif len(PeriodOrStart) > 5 and '-' in PeriodOrStart:
        fetch_kwargs['start'] = PeriodOrStart
        fetch_kwargs['period'] = None
    else:
        fetch_kwargs['period'] = PeriodOrStart
        fetch_kwargs['start'] = None

    cache_version_key = len(DISPLAY_COLUMNS)

    df_daily = get_all_prices_cached(
        followed_tickers,
        interval="1d",
        cache_version_key=cache_version_key,
        **fetch_kwargs
    )

    if df_daily.empty:
        return pd.DataFrame(), pd.DataFrame(), followed_tickers

    df_daily = calculate_all_indicators(df_daily)

    final_df_unformatted = df_daily.groupby('Ticker').tail(1).copy()

    # ⏱️ Forecast con cache
    forecast_df = _cached_forecast(final_df_unformatted)
    final_df_unformatted = final_df_unformatted.merge(
        forecast_df[['Ticker', 'Forecast Low', 'Forecast High']],
        on='Ticker',
        how='left'
    )

    start_prices = df_daily.groupby('Ticker')['Close'].first().reset_index()
    start_prices.rename(columns={'Close': 'Start Price'}, inplace=True)
    final_df_unformatted = final_df_unformatted.merge(start_prices, on='Ticker', how='left')

    if 'Dividends' in df_daily.columns:
        total_dividends = df_daily.groupby('Ticker')['Dividends'].sum().reset_index()
        total_dividends.rename(columns={'Dividends': 'Dividend'}, inplace=True)
        final_df_unformatted = final_df_unformatted.merge(total_dividends, on='Ticker', how='left')
        final_df_unformatted['Dividend'] = final_df_unformatted['Dividend'].fillna(0)
    else:
        final_df_unformatted['Dividend'] = 0

    if 'Sector' in tickers_df.columns and not final_df_unformatted.empty:
        final_df_unformatted = final_df_unformatted.merge(
            tickers_df[['Ticker', 'Sector']],
            on='Ticker',
            how='left'
        )
        if 'Sector_x' in final_df_unformatted.columns:
            final_df_unformatted['Sector'] = final_df_unformatted['Sector_y']
            final_df_unformatted.drop(columns=['Sector_x', 'Sector_y'], inplace=True)

    final_df = _format_final_df(final_df_unformatted)

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

        st.altair_chart(chart, width='stretch')
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
            "MarketCap": st.column_config.NumberColumn("Market Cap", format="$%.1f B", width="small"),
            "Beta": st.column_config.NumberColumn("Beta", format="%.2f", width="small"),
            "Start Price": st.column_config.NumberColumn("First", help="First price of the lookback period", format="$%.2f", width="small"),
            "Close": st.column_config.NumberColumn("Last", help="Last price of the lookback period", format="$%.2f", width="small"),
            "Dividend": st.column_config.NumberColumn("Dividends", help="Total dividends received during the lookback period.", format="$%.2f",width="small"),            
            "Forecast Low": st.column_config.NumberColumn("Forecast Low", format="$%.2f", width="small"),
            "Forecast High": st.column_config.NumberColumn("Forecast High", format="$%.2f",width="small"),                       
            "Avg Return": st.column_config.NumberColumn("AAR%", help="Annualized Average return", format="%.2f%%", width="small"),
            "Annualized Vol": st.column_config.NumberColumn("Vol%", help="Annualized Average volatility", format="%.2f%%", width="small"),
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
        
        st.markdown("**1. First**")
        st.info("The Adjusted Close Price on the **first day** of the selected Lookback Period. Used as the base for all period-related returns")
        
        st.markdown("**2. Last**")
        st.info("The latest Adjusted Close Price.")      
        
        st.markdown("**3. Dividends**")
        st.info("The **Total Sum of Dividends** paid out per share for the stock over the entire Lookback Period.")
        

        st.markdown("**4. Forecast High / Forecast Low**")
        st.info("The max/min price forecast range based on MonteCarlo simulation for a 1 month time horizon.")
        
        st.markdown("**5. Avg Return (AAR%) / Annualized Vol (Vol%)**")
        st.info("These metrics are calculated using the daily logarithmic returns over the Lookback Period and are then **annualized** for comparison (assumes 252 trading days/year).")
        
        st.markdown("**6. Sharpe Ratio**")
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
    st.title("📊 TradeSentinel demo")
    # Guide section in sidebar
    render_info_section()

    # User Input for Data Period
        
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

        # Pack both dates into a tuple or list string to pass as the argument
        period_arg = f"{custom_start_date}|{custom_end_date}" 

    st.markdown("---") # Separator for cleaner UI
    
    # Load and process all data required for the main display
    # Pass the custom period/date argument
    final_df, df_daily, followed_tickers = _load_and_process_data(PeriodOrStart=period_arg)
  
    # Save the period_arg into the session state
    st.session_state['main_dashboard_period_arg'] = period_arg 

    # Info section
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
        st.info("No data found.")
        
    # Credits
    st.markdown("---")
    st.markdown(
        "🔗 [View Source Code on GitHub](https://github.com/sebakremis/TradeSentinel)",
        unsafe_allow_html=True
    )
    st.markdown("👤 Developed by Sebastian Kremis")
    st.caption("Built using Streamlit and Python. NO investment advice. For educational/demo purposes only.")
    
    

if __name__ == "__main__":
    main()