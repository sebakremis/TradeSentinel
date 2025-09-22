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

    with st.expander("Indicator Settings"):
        st.markdown("---")
        ema_fast_period = st.number_input("Fast EMA Period", min_value=1, value=20, step=1)
        ema_slow_period = st.number_input("Slow EMA Period", min_value=1, value=50, step=1)
        st.markdown("---")

    st.subheader("")
    
    df_daily = pd.DataFrame()
    df_intraday = pd.DataFrame()
    
    if st.session_state.data_fetched:
        df_daily = load_all_prices('1d')
        df_intraday = load_all_prices('30m')
            
    if not df_daily.empty and not df_intraday.empty:
        st.success("✅ Dashboard data is ready.")

        daily_interval = '1d'
        intraday_interval = '30m'

        if 'Date' not in df_daily.columns:
            df_daily = df_daily.reset_index(names=['Date'])
        df_daily = calculate_price_change(df_daily)
        df_daily = trend(df_daily, fast_n=ema_fast_period, slow_n=ema_slow_period)
        df_daily = ema(df_daily, ema_fast_period)
        df_daily = distance_from_ema(df_daily)
        last_daily_df = df_daily.groupby('Ticker').tail(1).copy()

        if 'Date' not in df_intraday.columns:
            df_intraday = df_intraday.reset_index(names=['Date'])
        df_intraday = trend(df_intraday, fast_n=ema_fast_period, slow_n=ema_slow_period)
        last_intraday_df = df_intraday.groupby('Ticker').tail(1).copy()

        merged_df = pd.merge(
            last_daily_df.rename(columns={'Close': 'Last', 'Trend': 'Trend_1d'}),
            last_intraday_df.rename(columns={'Close': 'Close_30m', 'Trend': 'Trend_30m'}),
            on='Ticker',
            how='outer'
        )

        expected_columns = ['Ticker', 'Last', 'Change %', 'Trend_1d', 'Trend_30m', 'Distance_Ema20']
        for col in expected_columns:
            if col not in merged_df.columns:
                merged_df[col] = np.nan

        display_columns = ['Ticker', 'Last', 'Change %', 'Trend_1d', 'Trend_30m', 'Distance_Ema20']
        final_df = merged_df[display_columns].copy()
        final_df['Last'] = final_df['Last'].round(2)
        final_df['Distance_Ema20'] = final_df['Distance_Ema20'].round(2)
        final_df['Change %'] = final_df['Change %'].round(2)
        final_df = final_df.sort_values(by='Ticker')
        st.subheader("")

        col1_filters, col2_filters, col3_filters = st.columns(3)
        filtered_df = final_df.copy()
        trend_1d_options = filtered_df['Trend_1d'].dropna().unique().tolist()
        trend_1d_options.insert(0, 'All')
        default_index_1d = trend_1d_options.index('long') if 'long' in trend_1d_options else 0
        selected_trend_1d = col1_filters.selectbox("Filter by 1d Trend", trend_1d_options, index=default_index_1d)

        trend_30m_options = filtered_df['Trend_30m'].dropna().unique().tolist()
        trend_30m_options.insert(0, 'All')
        default_index_30m = trend_30m_options.index('long') if 'long' in trend_30m_options else 0
        selected_trend_30m = col2_filters.selectbox("Filter by 30m Trend", trend_30m_options, index=default_index_30m)

        sort_options = ['Ticker', 'Change %', 'Last', 'Distance_Ema20']
        default_sort_index = sort_options.index('Distance_Ema20')
        selected_sort = col3_filters.selectbox("Sort By", sort_options, index=default_sort_index)

        if selected_trend_1d != 'All':
            filtered_df = filtered_df[filtered_df['Trend_1d'] == selected_trend_1d]
        if selected_trend_30m != 'All':
            filtered_df = filtered_df[filtered_df['Trend_30m'] == selected_trend_30m]
        filtered_df = filtered_df.sort_values(by=selected_sort)
        col_select, col_table = st.columns([1, 2])
        with col_select:
            st.subheader("Add to Portfolio Simulator")
            selected_tickers = []
            with st.container(border=True, height=300):
                for _, row in filtered_df.iterrows():
                    ticker = row['Ticker']
                    if st.checkbox(f"**{ticker}**", key=f"checkbox_{ticker}"):
                        selected_tickers.append(ticker)

        with col_table:
            st.subheader("")
            st.dataframe(
                filtered_df,
                hide_index=True,
                width='stretch',
                column_config={
                    "Ticker": st.column_config.TextColumn("Ticker"),
                    "Last": st.column_config.NumberColumn("Last", format="%.2f"),
                    "Change %": st.column_config.NumberColumn("Change %", format="%.2f%%"),
                    "Trend_1d": st.column_config.TextColumn("Trend_1d"),
                    "Trend_30m": st.column_config.TextColumn("Trend_30m"),
                    "Distance_Ema20": st.column_config.NumberColumn("Distance_Ema20", format="%.2f%%"),
                }
            )

        if st.button("Simulate Portfolio", disabled=not selected_tickers):
            if selected_tickers:
                total_investment = 100000
                portfolio_tuples = calculate_portfolio(selected_tickers, filtered_df, total_investment)
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

        # Updated: Replace text input with selectbox for removing tickers
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














