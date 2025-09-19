import streamlit as st
import pandas as pd

from src.storage import save_prices_incremental
from src.data_fetch import get_market_data
from src.dashboard_manager import intervals_full, intervals_main, load_all_prices
from src.tickers_store import load_followed_tickers
from src.config import BASE_DIR
from src.indicators import calculate_price_change


def main():
    st.title("📊 TradeSentinel Dashboard")

    # Detect available intervals
    available_intervals = [p.name for p in BASE_DIR.iterdir() if p.is_dir()] if BASE_DIR.exists() else []

    if available_intervals:
        # Box to select interval
        interval = st.radio("Select interval", available_intervals)
        df = load_all_prices(interval)

        if not df.empty:
            st.subheader(f"Market Data ({interval})")
            
            # --- START OF MODIFIED CODE ---

            # Create a copy to avoid modifying the original DataFrame
            display_df = df.copy()

            # Reset the index to make 'Date' a column, preventing KeyError
            if display_df.index.name is not None:
                display_df = display_df.reset_index(names=[display_df.index.name])
            else:
                display_df = display_df.reset_index(names=['Date'])
            
            # Call the new function from indicators.py to add calculated columns
            display_df = calculate_price_change(display_df)

            # Get the last price for each unique ticker
            last_prices_df = display_df.groupby('Ticker').tail(1).copy()
            
            # Define the columns to display
            display_columns = ['Ticker', 'Close', 'Change', 'Change %', 'Date']

            # Select only the columns you want to display
            final_df = last_prices_df[display_columns].copy()

            # Round the numeric columns
            final_df['Change'] = final_df['Change'].round(2)
            final_df['Change %'] = final_df['Change %'].round(2)

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
            styled_df = final_df.style.applymap(color_change, subset=['Change', 'Change %'])

            styled_df = styled_df.format({
                'Close': '{:.2f}',
                'Change': '{:.2f}',
                'Change %': '{:.2f}%'
            })

            # Display the styled DataFrame
            st.dataframe(styled_df, hide_index=True)

            # --- END OF MODIFIED CODE ---
                
        else:
            st.info(f"No data found for interval {interval}.")
    else:
        st.info("No market data found in database yet.")

    # Update button
    if st.button("Update Prices"):
        tickers = load_followed_tickers()
        if not tickers:
            st.warning("⚠️ No tickers found in followed_tickers_test.csv")
        
        for ticker in tickers:
            for period, interval in intervals_main.items():
                st.write(f"Fetching {ticker} with period={period}, interval={interval} …")
        
                # Fetch with period (Yahoo requirement)
                data = get_market_data(ticker, interval=interval, period=period)
        
                if not data.empty:
                    # Save under interval folder (e.g. data/prices/30m/, data/prices/1d/)
                    save_prices_incremental(ticker, interval, data)
                    st.success(f"✅ Saved {ticker} {interval} ({period})")
                else:
                    st.warning(f"⚠️ No data for {ticker} {period}/{interval}")
        
        st.rerun()

if __name__ == "__main__":
    main()









