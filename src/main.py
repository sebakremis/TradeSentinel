# src/main.py
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

from src.config import DATA_DIR
from src.dashboard_manager import load_all_prices, get_all_prices_cached
from src.tickers_manager import load_followed_tickers, add_ticker, remove_ticker, TickerValidationError
from src.indicators import calculate_price_change, ema, trend, higher_high, distance_higher_high
from src.sim_portfolio import calculate_portfolio

def main():
    st.title("📊 TradeSentinel: Market View")

    if 'data_fetched' not in st.session_state:
        st.session_state.data_fetched = False

    ema_fast_period = 20
    ema_slow_period = 50
    
    
    df_daily = pd.DataFrame()
    if st.session_state.data_fetched:
        df_daily = load_all_prices()
    
    if not df_daily.empty:
        st.success("✅ Dashboard data is ready.")

        if 'Date' not in df_daily.columns:
            df_daily = df_daily.reset_index(names=['Date'])
        
        df_daily = calculate_price_change(df_daily)
        df_daily = trend(df_daily, fast_n=ema_fast_period, slow_n=ema_slow_period)
        df_daily = ema(df_daily, ema_fast_period)
        df_daily = higher_high(df_daily)
        df_daily = distance_higher_high(df_daily)
        
        # Create a copy for the final display
        final_df = df_daily.groupby('Ticker').tail(1).copy()
        
        # Ensure required columns exist and are formatted
        expected_columns = ['Ticker', 'Close', 'Change %', 'Trend', 'HigherHigh', 'Distance']
        for col in expected_columns:
            if col not in final_df.columns:
                final_df[col] = np.nan
        
        display_columns = ['Ticker', 'Close', 'Change %', 'Trend', 'HigherHigh', 'Distance']
        final_df = final_df[display_columns].copy()
        
        final_df['Close'] = final_df['Close'].round(2)
        final_df['HigherHigh'] = final_df['HigherHigh'].round(2)
        final_df['Distance'] = final_df['Distance'].round(2)
        final_df['Change %'] = final_df['Change %'].round(2)
        
        st.subheader("")
        
        sorted_df = final_df.sort_values(by='Distance', ascending=True)

        # Refactored to use st.data_editor for interactive selection
        display_df = sorted_df.copy()
        display_df['Select'] = False # Add a new 'Select' column for checkboxes

        edited_df = st.data_editor(
            display_df,
            hide_index=True,
            width='stretch',
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker"),
                "Close": st.column_config.NumberColumn("Close", format="%.2f"),
                "Change %": st.column_config.NumberColumn("Change %", format="%.2f%%"),
                "Trend": st.column_config.TextColumn("Trend"),
                "HigherHigh": st.column_config.NumberColumn("HigherHigh", format="%.2f"),
                "Distance": st.column_config.NumberColumn("Distance", format="%.2f%%"),
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
    else:
        st.info("No data found. Click 'Update Prices' to fetch data.")

    st.subheader("Tickers Management")
    tickers_df = load_followed_tickers()
    col1_followed, col2_buttons = st.columns(2)
    with col1_followed:
        st.markdown("**Followed Tickers:**")
        if not tickers_df.empty:
            followed_tickers_str = ', '.join(tickers_df['Ticker'].tolist())
            st.markdown(followed_tickers_str)
        else:
            st.markdown("No followed tickers found.")

    with col2_buttons:
        if st.button("Update Prices", key='update_button'):
            if tickers_df.empty:
                st.warning("⚠️ No tickers found to update.")
            else:
                with st.spinner("Fetching all ticker data..."):
                    get_all_prices_cached.clear()
                    st.session_state.data_fetched = True
                st.rerun()
                st.success("✅ Data fetch and processing complete.")

        new_ticker = st.text_input("Enter Ticker Symbol to Add", max_chars=5, key='add_ticker_input').upper().strip()
        if st.button("Add Ticker", key='add_button'):
            if new_ticker:
                try:
                    add_ticker(new_ticker)
                    st.success(f"✅ Added ticker {new_ticker}")
                    st.session_state['add_ticker_input'] = ""
                except TickerValidationError as e:
                    st.error(f"❌ {e}")
                except Exception as e:
                    st.error(f"❌ An unexpected error occurred: {e}")
                st.rerun()
            else:
                st.warning("Please enter a ticker symbol to add.")

        ticker_list_to_remove = tickers_df['Ticker'].tolist()
        rem_ticker_select = st.selectbox("Select Ticker Symbol to Remove", options=ticker_list_to_remove, key='rem_ticker_select')
        
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

if __name__ == "__main__":
    main()














