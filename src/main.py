import streamlit as st
import pandas as pd
import numpy as np

from src.storage import save_prices_incremental
from src.data_fetch import get_market_data
from src.dashboard_manager import intervals_full, intervals_main, load_all_prices
from src.tickers_store import load_followed_tickers
from src.config import BASE_DIR, DATA_DIR
from src.indicators import calculate_price_change, ema, trend,distance_from_ema
from src.sim_portfolio import calculate_portfolio

def main():
    # The entire main dashboard logic goes here
    # No if-elif routing for pages is needed
    st.title("📊 TradeSentinel: Market View")

    # Add a number input for the EMA periods
    with st.expander("Indicator Settings"):
        st.markdown("---")
        ema_fast_period = st.number_input("Fast EMA Period", min_value=1, value=20, step=1)
        ema_slow_period = st.number_input("Slow EMA Period", min_value=1, value=50, step=1)
        st.markdown("---")

    st.subheader("") # "Combined Market Data"

    # Define the intervals to be displayed on the dashboard
    daily_interval = '1d'
    intraday_interval = '30m'

    # Load daily data and perform calculations
    df_daily = load_all_prices(daily_interval)
    if not df_daily.empty:
        # Prepare DataFrame for calculations
        if df_daily.index.name is not None:
            df_daily = df_daily.reset_index(names=[df_daily.index.name])
        else:
            df_daily = df_daily.reset_index(names=['Date'])

        # Perform trend calculation on daily data
        df_daily = calculate_price_change(df_daily)
        df_daily = trend(df_daily, fast_n=ema_fast_period, slow_n=ema_slow_period)

        # calculate distance to fast ema
        df_daily = ema(df_daily,ema_fast_period)
        df_daily = distance_from_ema(df_daily)

        # Extract last row for each ticker from daily data
        last_daily_df = df_daily.groupby('Ticker').tail(1).copy()

    else:
        st.warning("Daily data (1d) not found. Please update.")
        # Create a placeholder DataFrame with the expected columns
        last_daily_df = pd.DataFrame(columns=['Ticker', 'Close', 'Change %', 'Trend', 'Distance_Ema20'])

    # Load intraday data and perform calculations
    df_intraday = load_all_prices(intraday_interval)
    if not df_intraday.empty:
        # Prepare DataFrame for calculations
        if df_intraday.index.name is not None:
            df_intraday = df_intraday.reset_index(names=[df_intraday.index.name])
        else:
            df_intraday = df_intraday.reset_index(names=['Date'])

        # Perform price change calculation on intraday data
        df_intraday = trend(df_intraday, fast_n=ema_fast_period, slow_n=ema_slow_period)

        # Extract last row for each ticker from intraday data
        last_intraday_df = df_intraday.groupby('Ticker').tail(1).copy()

    else:
        st.warning("Intraday data (30m) not found. Please update.")
        # Create a placeholder DataFrame with the expected columns
        last_intraday_df = pd.DataFrame(columns=['Ticker', 'Trend'])

    # Merge the two DataFrames on 'Ticker' to create a single display table
    merged_df = pd.merge(
        last_daily_df.rename(columns={'Close': 'Last', 'Trend': 'Trend_1d'}),
        last_intraday_df.rename(columns={'Close': 'Close_30m', 'Trend': 'Trend_30m'}),
        on='Ticker',
        how='outer'
    )

    # Define a list of all required columns to prevent KeyErrors
    expected_columns = ['Ticker', 'Last', 'Change %', 'Trend_1d','Trend_30m','Distance_Ema20']

    # Add missing columns with NaN values
    for col in expected_columns:
        if col not in merged_df.columns:
            merged_df[col] = np.nan

    # Check if the final merged DataFrame is empty
    if not merged_df.empty:
        # Define columns to display from the merged DataFrame
        display_columns = ['Ticker', 'Last', 'Change %', 'Trend_1d','Trend_30m', 'Distance_Ema20']

        final_df = merged_df[display_columns].copy()

        # Round numeric columns for display
        final_df['Last'] = final_df['Last'].round(2)
        final_df['Distance_Ema20'] = final_df['Distance_Ema20'].round(2)
        final_df['Change %'] = final_df['Change %'].round(2)

        # Sort the DataFrame by 'Ticker' alphabetically
        final_df = final_df.sort_values(by='Ticker')

        # --- Start of new filter and sort section ---
        st.subheader("") #'Data Filters and Sorting'

        col1_filters, col2_filters, col3_filters = st.columns(3)

        # Initialize filtered_df here, so it is always defined
        filtered_df = final_df.copy()

        # Filter by 1d Trend
        trend_1d_options = filtered_df['Trend_1d'].dropna().unique().tolist()
        trend_1d_options.insert(0, 'All')

        # Get the index of 'long' for the default value
        default_index_1d = trend_1d_options.index('long') if 'long' in trend_1d_options else 0
        selected_trend_1d = col1_filters.selectbox(
            "Filter by 1d Trend",
            trend_1d_options,
            index=default_index_1d
        )

        # Filter by 30m Trend
        trend_30m_options = filtered_df['Trend_30m'].dropna().unique().tolist()
        trend_30m_options.insert(0, 'All')

        # Get the index of 'long' for the default value
        default_index_30m = trend_30m_options.index('long') if 'long' in trend_30m_options else 0
        selected_trend_30m = col2_filters.selectbox(
            "Filter by 30m Trend",
            trend_30m_options,
            index=default_index_30m
        )

        # Add a selectbox for sorting
        sort_options = ['Ticker', 'Change %', 'Last', 'Distance_Ema20']

        # Get the index of 'Distance_Ema20' for the default value
        default_sort_index = sort_options.index('Distance_Ema20')
        selected_sort = col3_filters.selectbox(
            "Sort By",
            sort_options,
            index=default_sort_index
        )

        # Apply the filters
        if selected_trend_1d != 'All':
            filtered_df = filtered_df[filtered_df['Trend_1d'] == selected_trend_1d]

        if selected_trend_30m != 'All':
            filtered_df = filtered_df[filtered_df['Trend_30m'] == selected_trend_30m]

        # Apply the selected sorting
        filtered_df = filtered_df.sort_values(by=selected_sort)

        # --- End of new filter and sort section ---

        # --- New selection and action section ---
        # Create two columns for the side-by-side layout
        col_select, col_table = st.columns([1, 2])

        # Place the selection logic in the first column
        with col_select:
            st.subheader("Add to Portfolio Simulator")
            # Store the selected tickers in a list
            selected_tickers = []

            # Use a container to display a checkable list of tickers
            with st.container(border=True, height=300):
                for _, row in filtered_df.iterrows():
                    ticker = row['Ticker']
                    # Use the key parameter to ensure state is maintained
                    if st.checkbox(f"**{ticker}**", key=f"checkbox_{ticker}"):
                        selected_tickers.append(ticker)

        # Place the styled DataFrame in the second column
        with col_table:
            st.subheader("") # "Filtered Data"
            st.dataframe(
                filtered_df, # Pass the unstyled DataFrame here
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Ticker": st.column_config.TextColumn("Ticker"),
                    "Last": st.column_config.NumberColumn("Last", format="%.2f"),
                    "Change %": st.column_config.NumberColumn("Change %", format="%.2f%%"),
                    "Trend_1d": st.column_config.TextColumn("Trend_1d"),
                    "Trend_30m": st.column_config.TextColumn("Trend_30m"),
                    "Distance_Ema20": st.column_config.NumberColumn("Distance_Ema20", format="%.2f%%"),
                }
            )

        # The action button should be placed outside the columns to span the full width
        if st.button("Simulate Portfolio", disabled=not selected_tickers):
            if selected_tickers:
                total_investment = 100000
                # Call the calculation function to get the list of tuples
                portfolio_tuples = calculate_portfolio(selected_tickers, filtered_df, total_investment)
                
                # Store the result in session state
                st.session_state['portfolio'] = portfolio_tuples
                
                # Switch to the new page using its name
                st.switch_page("pages/02_Portfolio_Dashboard.py")
            else:
                st.warning("Please select at least one ticker.")
    # --- End of new selection and action section ---

    else:
        st.info("No data found for any of the selected intervals.")
        
    # Update button
    if st.button("Update Prices"):
        tickers_df = load_followed_tickers()
        if tickers_df.empty:
            st.warning("⚠️ No tickers found to update.")
        else:
            tickers = tickers_df['Ticker'].tolist()
            # Define periods for each interval.
            periods = {'1d': '1y', '30m': '5d'}

            for ticker in tickers:
                for interval, interval_full_name in intervals_main.items():
                    period = periods.get(interval, '1d')
                    st.write(f"Fetching {ticker} with period={period}, interval={interval} …")

                    data = get_market_data(ticker, interval=interval, period=period)

                    if not data.empty:
                        save_prices_incremental(ticker, interval, data)
                        st.success(f"✅ Saved {ticker} {interval} ({period})")
                    else:
                        st.warning(f"⚠️ No data for {ticker} {period}/{interval}")

            st.rerun()

if __name__ == "__main__":
    main()














