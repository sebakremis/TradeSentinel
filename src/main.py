# src/main.py
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Import all necessary modules
from src.dashboard_manager import get_all_prices_cached, calculate_all_indicators
from src.tickers_manager import load_followed_tickers, add_ticker, remove_ticker, TickerValidationError
from src.sim_portfolio import calculate_portfolio

# Global constants
EMA_FAST_PERIOD = 20
EMA_SLOW_PERIOD = 50
DISPLAY_COLUMNS = DISPLAY_COLUMNS = ['Ticker', 'Close', 'Change %', 'Avg Return', 'Annualized Vol', 'Sharpe Ratio', 'Trend', 'Highest Close', 'Lowest Close', 'Distance HC' ]

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
    
    # Select only the display columns
    df = df[DISPLAY_COLUMNS]

    # Apply rounding
    if 'Close' in df.columns:
        df['Close'] = df['Close'].round(2)
    if 'Highest Close' in df.columns:
        df['Highest Close'] = df['Highest Close'].round(2)
    
    # Rounding percentage/ratio columns
    for col in ['Distance HC', 'Change %', 'Avg Return', 'Annualized Vol', 'Sharpe Ratio']:
        if col in df.columns:
            df[col] = df[col].round(2)
            
    return df

def _load_and_process_data(PeriodOrStart= "1y") -> (pd.DataFrame, pd.DataFrame, list): 
    
    tickers_df = load_followed_tickers()
    followed_tickers = tickers_df['Ticker'].tolist() if not tickers_df.empty else []
    
    # Determine which argument to pass to the data fetcher
    fetch_kwargs = {}
    
    # 🚨 UPDATED LOGIC TO HANDLE START|END DATE STRING
    if '|' in PeriodOrStart:
        # Custom Start and End Dates were provided (e.g., '2024-01-01|2024-10-01')
        start_date, end_date = PeriodOrStart.split('|')
        fetch_kwargs['start'] = start_date
        fetch_kwargs['end'] = end_date # New argument for end date
        fetch_kwargs['period'] = None
        
    elif len(PeriodOrStart) > 5 and '-' in PeriodOrStart: 
        # Only a Custom Start Date was provided (if we had kept the previous logic)
        # This branch can technically be removed if 'Custom Date' always passes start|end
        fetch_kwargs['start'] = PeriodOrStart
        fetch_kwargs['period'] = None
    else:
        # Preset Period String ('1y', '3mo', etc.)
        fetch_kwargs['period'] = PeriodOrStart
        fetch_kwargs['start'] = None
        
    df_daily = get_all_prices_cached(
        followed_tickers, 
        interval="1d",
        **fetch_kwargs # Pass either 'period' or 'start' and 'end'
    )
    
    if df_daily.empty:
        return pd.DataFrame(), pd.DataFrame(), followed_tickers 

    # 1. Calculate indicators (operates on the full df_daily)
    # Ensure this function also returns the full, enriched df_daily
    df_daily = calculate_all_indicators(df_daily, EMA_FAST_PERIOD, EMA_SLOW_PERIOD) 
    
    # 2. Get the latest snapshot (one row per ticker)
    final_df_unformatted = df_daily.groupby('Ticker').tail(1).copy()
    
    # 3. Format the data for display
    final_df = _format_final_df(final_df_unformatted)
    
    # 🚨 NEW: Return both the snapshot (final_df) and the full daily data (df_daily)
    return final_df, df_daily, followed_tickers 


# ----------------------------------------------------------------------
# --- UI Rendering Functions ---
# ----------------------------------------------------------------------

def _render_overview_section(final_df: pd.DataFrame):
    """Renders the risk-return scatter plot."""
    st.subheader("Followed Tickers Overview")

    if not final_df.empty and 'Avg Return' in final_df.columns and 'Annualized Vol' in final_df.columns:
        # Create the scatter plot using Altair
        chart = alt.Chart(final_df).mark_point(size=100).encode(
            x=alt.X('Annualized Vol', title='Annualized Volatility (%)'),
            y=alt.Y('Avg Return', title='Annualized Average Return (%)'),
            tooltip=['Ticker', 'Avg Return', 'Annualized Vol'],
            color=alt.Color('Ticker', legend=None)
        ).properties(
            title='Risk vs. Return'
        ).interactive()

        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("Cannot generate risk-return plot. Ensure tickers are selected and data is loaded.")


def _render_summary_table_and_portfolio(final_df: pd.DataFrame, df_daily: pd.DataFrame):
    """Renders the summary table and portfolio simulation controls."""
    st.subheader("Summary Table")

    
    if final_df.empty:
        st.info("No data available to display in the summary table.")
        return

    sorted_df = final_df.sort_values(by='Sharpe Ratio', ascending=False)

    display_df = sorted_df.copy()
    display_df['Select'] = False

    edited_df = st.data_editor(
        display_df,
        hide_index=True,
        width='stretch',
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker"),
            "Close": st.column_config.NumberColumn("Close", format="%.2f"),
            "Change %": st.column_config.NumberColumn("Change %", format="%.2f%%"),
            "Avg Return": st.column_config.NumberColumn("Avg Return", format="%.2f%%"),
            "Annualized Vol": st.column_config.NumberColumn("Annualized Vol", format="%.2f%%"),
            "Sharpe Ratio": st.column_config.NumberColumn("Sharpe Ratio", format="%.2f%%"),
            "Trend": st.column_config.TextColumn("Trend"),
            "Highest Close": st.column_config.NumberColumn("Highest Close", format="%.2f"),
            "Distance HC": st.column_config.NumberColumn("Distance HC", format="%.2f%%"),
            "Select": st.column_config.CheckboxColumn("Select", default=False)
        },
        num_rows="fixed"
    )
    
    selected_tickers_df = edited_df[edited_df['Select']]
    selected_tickers = selected_tickers_df['Ticker'].tolist()

    if st.button("Simulate Portfolio", disabled=not selected_tickers):
        if selected_tickers:
            total_investment = 100000
            # 🚨 NEW: Pass the full daily data to the calculation function
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


# ----------------------------------------------------------------------
# --- Main Dashboard Function ---
# ----------------------------------------------------------------------

def main():
    st.set_page_config(layout="wide")
    st.title("📊 TradeSentinel: Main Dashboard")

    # --------------------------------------------------------------
    # User Input for Data Period (Revised Section for Start/End Date)
    # --------------------------------------------------------------
    
    # Define selectable periods (common Yahoo Finance periods)
    AVAILABLE_PERIODS = ["1mo", "3mo", "6mo", "ytd", "1y", "2y", "5y", "Custom Date"]
    
    # 1. Period Selection
    selected_period = st.selectbox(
        "Select Lookback Period for Analysis", 
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

        # 🚨 CHANGE: Pack both dates into a tuple or list string to pass as the argument
        # We will need to update _load_and_process_data to handle this specific format.
        period_arg = f"{custom_start_date}|{custom_end_date}" 

    st.markdown("---") # Separator for cleaner UI
    
    # Load and process all data required for the main display
    # Pass the custom period/date argument
    final_df, df_daily, followed_tickers = _load_and_process_data(PeriodOrStart=period_arg)

    if not final_df.empty:
        # Render the display sections if data is present
        _render_overview_section(final_df)
        _render_summary_table_and_portfolio(final_df, df_daily) # 🚨 NEW: Pass df_daily to the summary table function
    else:
        st.info("No data found. Add a ticker using the management controls below and click 'Update Prices' to fetch data.")
        
    # Tickers management and Update Prices are always visible
    _render_ticker_management_section(followed_tickers)
    
    


if __name__ == "__main__":
    main()