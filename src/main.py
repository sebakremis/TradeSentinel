# src/main.py
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

from src.config import DATA_DIR
from src.dashboard_manager import load_all_prices, get_all_prices_cached
from src.tickers_store import load_followed_tickers, add_ticker, remove_ticker, TickerValidationError
from src.indicators import calculate_price_change, ema, trend, distance_from_ema
from src.sim_portfolio import calculate_portfolio

def main():
    st.title("📊 TradeSentinel: Market View")

    if 'data_fetched' not in st.session_state:
        st.session_state.data_fetched = False

    ema_fast_period = 20
    ema_mid_period = 50
    ema_slow_period = 100
    
    df_daily = pd.DataFrame()
    if st.session_state.data_fetched:
        df_daily = load_all_prices()
    
    if not df_daily.empty:
        st.success("✅ Dashboard data is ready.")

        if 'Date' not in df_daily.columns:
            df_daily = df_daily.reset_index(names=['Date'])
        
        df_daily = calculate_price_change(df_daily)
        df_daily = trend(df_daily, fast_n=ema_fast_period, mid_n=ema_mid_period, slow_n=ema_slow_period)
        df_daily = ema(df_daily, ema_fast_period)
        df_daily = distance_from_ema(df_daily)
        
        # Create a copy for the final display
        final_df = df_daily.groupby('Ticker').tail(1).copy()
        
        # Ensure required columns exist and are formatted
        expected_columns = ['Ticker', 'Close', 'Change %', 'Trend', 'Distance_Ema20']
        for col in expected_columns:
            if col not in final_df.columns:
                final_df[col] = np.nan
        
        display_columns = ['Ticker', 'Close', 'Change %', 'Trend', 'Distance_Ema20']
        final_df = final_df[display_columns].copy()
        
        final_df['Close'] = final_df['Close'].round(2)
        final_df['Distance_Ema20'] = final_df['Distance_Ema20'].round(2)
        final_df['Change %'] = final_df['Change %'].round(2)
        
        st.subheader("")

        col1_filters, col2_filters = st.columns(2)
        
        # Create a separate DataFrame for filtering
        filtered_df = final_df.copy()
        
        
            
        col_select, col_table = st.columns([1, 2])
        
        with col_select:
            st.subheader("Add to Portfolio Simulator")
            selected_tickers = []
            with st.container(border=True, height=300):
                # The crucial fix: iterate over the full, unfiltered final_df
                # to ensure checkbox keys are stable across reruns.
                for _, row in filtered_df.iterrows():
                    ticker = row['Ticker']
                    if st.checkbox(f"**{ticker}**", key=f"checkbox_{ticker}"):
                        selected_tickers.append(ticker)

        with col_table:
            st.subheader("")
            st.dataframe(
                # Use the filtered_df here for display
                filtered_df,
                hide_index=True,
                width='stretch',
                column_config={
                    "Ticker": st.column_config.TextColumn("Ticker"),
                    "Close": st.column_config.NumberColumn("Close", format="%.2f"),
                    "Change %": st.column_config.NumberColumn("Change %", format="%.2f%%"),
                    "Trend": st.column_config.TextColumn("Trend"),
                    "Distance_Ema20": st.column_config.NumberColumn("Distance_Ema20", format="%.2f%%"),
                }
            )

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














