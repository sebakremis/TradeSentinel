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
DISPLAY_COLUMNS = ['Ticker', 'Close', 'Change %', 'Avg Return', 'Annualized Vol', 'Sharpe Ratio', 'Trend', 'Highest Close', 'Distance HC' ] 

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

def _load_and_process_data(Period= "1d") -> (pd.DataFrame, list):
    """
    Loads followed tickers, fetches price data, applies indicators, 
    and returns the final formatted DataFrame snapshot.
    """
    tickers_df = load_followed_tickers()
    followed_tickers = tickers_df['Ticker'].tolist() if not tickers_df.empty else []

    df_daily = get_all_prices_cached(
        followed_tickers, 
        period=Period,
        interval="1d"
    )

    if df_daily.empty:
        return pd.DataFrame(), followed_tickers # Return empty DF and list

    # 1. Calculate indicators
    df_daily = calculate_all_indicators(df_daily, EMA_FAST_PERIOD, EMA_SLOW_PERIOD)
    
    # 2. Get the latest snapshot (one row per ticker)
    final_df_unformatted = df_daily.groupby('Ticker').tail(1).copy()
    
    # 3. Format the data for display
    final_df = _format_final_df(final_df_unformatted)
    
    return final_df, followed_tickers


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


def _render_summary_table_and_portfolio(final_df: pd.DataFrame):
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
            portfolio_tuples = calculate_portfolio(selected_tickers, final_df, total_investment)
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


def _render_update_prices_section(tickers_df: pd.DataFrame):
    """Renders the update prices button and logic."""
    st.markdown("---")
    st.markdown("### Update Prices")
    if st.button("Update Prices", key='update_button'):
        if tickers_df.empty:
            st.warning("⚠️ No tickers found to update.")
        else:
            with st.spinner("Fetching and updating all ticker data..."):
                # Clear all cached price data forcing a fresh download
                get_all_prices_cached.clear()
                # A simple flag to force a re-load, though st.rerun handles it primarily
                st.session_state.data_fetched = True 
            st.success("✅ Data fetch and processing complete.")
            st.rerun()


# ----------------------------------------------------------------------
# --- Main Dashboard Function ---
# ----------------------------------------------------------------------

def main():
    st.set_page_config(layout="wide")
    st.title("📊 TradeSentinel: Main Dashboard")

    # --------------------------------------------------------------
    # User Input for Data Period 
    # --------------------------------------------------------------
    
    # Define selectable periods (common Yahoo Finance periods)
    AVAILABLE_PERIODS = ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd"]
    
    # Create the selectbox for the user to choose the period
    selected_period = st.selectbox(
        "Select Lookback Period for Analysis", 
        options=AVAILABLE_PERIODS, 
        index=AVAILABLE_PERIODS.index("1y"), # Default to 1 year for richer analysis
        key='data_period_select'
    )
    
    st.markdown("---") # Separator for cleaner UI
    
    # Load and process all data required for the main display
    # Pass the selected period to the data processing function
    
    # Load and process all data required for the main display
    final_df, followed_tickers = _load_and_process_data(Period=selected_period)

    if not final_df.empty:
        # Render the display sections if data is present
        _render_overview_section(final_df)
        _render_summary_table_and_portfolio(final_df)
    else:
        st.info("No data found. Add a ticker using the management controls below and click 'Update Prices' to fetch data.")
        
    # Tickers management and Update Prices are always visible
    _render_ticker_management_section(followed_tickers)
    
    # Reload tickers_df to get the latest list for the Update Prices check
    latest_tickers_df = load_followed_tickers()
    _render_update_prices_section(latest_tickers_df)


if __name__ == "__main__":
    main()