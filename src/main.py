# src/main.py
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import altair as alt

# Assuming these imports are correctly set up
from src.config import DATA_DIR
from src.dashboard_manager import load_all_prices, get_all_prices_cached
from src.tickers_manager import load_followed_tickers, add_ticker, remove_ticker, TickerValidationError
from src.indicators import calculate_price_change, ema, trend, highest_close, distance_highest_close, annualized_metrics
from src.sim_portfolio import calculate_portfolio

def main():
    st.set_page_config(layout="wide")
    st.title("📊 TradeSentinel: Market View")

    ema_fast_period = 20
    ema_slow_period = 50
    
    tickers_df = load_followed_tickers()
    followed_tickers = tickers_df['Ticker'].tolist() if not tickers_df.empty else []

    df_daily = get_all_prices_cached(
        followed_tickers, 
        period="1y",
        interval="1d"
    )

    if not df_daily.empty:
        # st.success("✅ Dashboard data is ready.")

               
        # Now, the rest of the code should work as expected
        df_daily = calculate_price_change(df_daily)
        df_daily = trend(df_daily, fast_n=ema_fast_period, slow_n=ema_slow_period)
        df_daily = ema(df_daily, ema_fast_period)
        df_daily = highest_close(df_daily)
        df_daily = distance_highest_close(df_daily)
        df_daily = annualized_metrics(df_daily, n_days=200)
        
        final_df = df_daily.groupby('Ticker').tail(1).copy()
        
        expected_columns = ['Ticker', 'Close', 'Change %', 'Annualized Avg', 'Annualized Vol', 'Sharpe Ratio', 'Trend', 'Highest Close', 'Distance HC' ]
        for col in expected_columns:
            if col not in final_df.columns:
                final_df[col] = np.nan
        
        display_columns = ['Ticker', 'Close', 'Change %', 'Annualized Avg', 'Annualized Vol', 'Sharpe Ratio', 'Trend', 'Highest Close', 'Distance HC' ]
        final_df = final_df[display_columns].copy()
        
        final_df['Close'] = final_df['Close'].round(2)
        final_df['Highest Close'] = final_df['Highest Close'].round(2)
        final_df['Distance HC'] = final_df['Distance HC'].round(2)
        final_df['Change %'] = final_df['Change %'].round(2)
        final_df['Annualized Avg'] = final_df['Annualized Avg'].round(2)
        final_df['Annualized Vol'] = final_df['Annualized Vol'].round(2)
        final_df['Sharpe Ratio'] = final_df['Sharpe Ratio'].round(2)
        
        # --- NEW: RISK-RETURN SCATTER PLOT ---
        st.subheader("Followed Tickers Overview")

        if not final_df.empty and 'Annualized Avg' in final_df.columns and 'Annualized Vol' in final_df.columns:
            # Create the scatter plot using Altair
            chart = alt.Chart(final_df).mark_point(size=100).encode(
                x=alt.X('Annualized Vol', title='Annualized Volatility (%)'),
                y=alt.Y('Annualized Avg', title='Annualized Average Return (%)'),
                tooltip=['Ticker', 'Annualized Avg', 'Annualized Vol'], # Show data on hover
                color=alt.Color('Ticker', legend=None) # Color points by ticker
            ).properties(
                title='Risk vs. Return'
            ).interactive() # Enable zooming and panning

            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("Cannot generate risk-return plot. Ensure tickers are selected and data is loaded.")

        # --- Table ---
        st.subheader("Summary Table")
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
                "Annualized Avg": st.column_config.NumberColumn("Annualized Avg", format="%.2f%%"),
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
    else:
        st.info("No data found. Click 'Update Prices' to fetch data.")
    st.markdown("Select tickers to simulate an equally-weighted portfolio.")
    st.markdown("---")
    st.markdown("### Update Prices")
    if st.button("Update Prices", key='update_button'):
        if tickers_df.empty:
            st.warning("⚠️ No tickers found to update.")
        else:
            with st.spinner("Fetching and updating all ticker data..."):
                get_all_prices_cached.clear()
                st.session_state.data_fetched = True
            st.success("✅ Data fetch and processing complete.")
            st.rerun()
            
    st.markdown("---")
    st.subheader("Tickers Management")
    tickers_df = load_followed_tickers()
    
    # This section is now always visible
    st.markdown("**📝 Followed Tickers:**")
    if not tickers_df.empty:
        followed_tickers_list = tickers_df['Ticker'].tolist()
        
        # Display tickers in a grid-like structure using columns
        num_cols = 5
        cols = st.columns(num_cols)
        
        for i, ticker in enumerate(followed_tickers_list):
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
    

    # Buttons
    
    

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














