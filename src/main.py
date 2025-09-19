import streamlit as st
import pandas as pd
import numpy as np

from src.storage import save_prices_incremental
from src.data_fetch import get_market_data
from src.dashboard_manager import intervals_full, intervals_main, load_all_prices
from src.tickers_store import load_followed_tickers
from src.config import BASE_DIR, DATA_DIR
from src.indicators import calculate_price_change, ema, trend


def main():
    st.title("📊 TradeSentinel Dashboard")
    
    # Add a number input for the EMA periods
    with st.expander("Indicator Settings"):
        st.markdown("---")
        ema_fast_period = st.number_input("Fast EMA Period", min_value=1, value=20, step=1)
        ema_slow_period = st.number_input("Slow EMA Period", min_value=1, value=50, step=1)
        st.markdown("---")

    st.subheader("Combined Market Data")
    
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
        df_daily = trend(df_daily, fast_n=ema_fast_period, slow_n=ema_slow_period)
        
        # Extract last row for each ticker from daily data
        last_daily_df = df_daily.groupby('Ticker').tail(1).copy()
        
    else:
        st.warning("Daily data (1d) not found. Please update.")
        # Create a placeholder DataFrame with the expected columns
        last_daily_df = pd.DataFrame(columns=['Ticker', 'Close', 'Trend', f'EMA_{ema_fast_period}', f'EMA_{ema_slow_period}'])

    # Load intraday data and perform calculations
    df_intraday = load_all_prices(intraday_interval)
    if not df_intraday.empty:
        # Prepare DataFrame for calculations
        if df_intraday.index.name is not None:
            df_intraday = df_intraday.reset_index(names=[df_intraday.index.name])
        else:
            df_intraday = df_intraday.reset_index(names=['Date'])
        
        # Perform price change calculation on intraday data
        df_intraday = calculate_price_change(df_intraday)
        
        # Extract last row for each ticker from intraday data
        last_intraday_df = df_intraday.groupby('Ticker').tail(1).copy()
        
    else:
        st.warning("Intraday data (30m) not found. Please update.")
        # Create a placeholder DataFrame with the expected columns
        last_intraday_df = pd.DataFrame(columns=['Ticker', 'Close', 'Change', 'Change %'])

    # Merge the two DataFrames on 'Ticker' to create a single display table
    merged_df = pd.merge(
        last_daily_df.rename(columns={'Close': 'Close_1d'}), 
        last_intraday_df.rename(columns={'Close': 'Close_30m', 'Change': 'Change_30m', 'Change %': 'Change %_30m'}),
        on='Ticker', 
        how='outer'
    )
    
    # Define a list of all required columns to prevent KeyErrors
    expected_columns = ['Ticker', 'Close_1d', 'Trend', 'Change_30m', 'Change %_30m', 'Date_1d', 'Close_30m', 'Date_30m']

    # Add missing columns with NaN values
    for col in expected_columns:
        if col not in merged_df.columns:
            merged_df[col] = np.nan
    
    # Check if the final merged DataFrame is empty
    if not merged_df.empty:
        # Define columns to display from the merged DataFrame
        display_columns = ['Ticker', 'Close_1d', 'Trend', 'Change_30m', 'Change %_30m']
        
        final_df = merged_df[display_columns].copy()

        # Round numeric columns for display
        final_df['Close_1d'] = final_df['Close_1d'].round(2)
        final_df['Change_30m'] = final_df['Change_30m'].round(2)
        final_df['Change %_30m'] = final_df['Change %_30m'].round(2)

        # Sort the DataFrame by 'Ticker' alphabetically
        final_df = final_df.sort_values(by='Ticker')
        
        # Function to apply color
        def color_change(value):
            if isinstance(value, (int, float)):
                if value > 0:
                    return 'color: green;'
                elif value < 0:
                    return 'color: red;'
            return ''
            
        # Apply the style to the final DataFrame
        styled_df = final_df.style.applymap(color_change, subset=['Change_30m', 'Change %_30m'])
        styled_df = styled_df.format({
            'Close_1d': '{:.2f}',
            'Change_30m': '{:.2f}',
            'Change %_30m': '{:.2f}%'
        })
        
        # Display the styled DataFrame
        st.dataframe(styled_df, hide_index=True)
        
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









