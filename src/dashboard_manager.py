# src/dashboard_manager.py
import streamlit as st
import pandas as pd
import yfinance as yf
# New imports for concurrent processing
from concurrent.futures import ThreadPoolExecutor, as_completed 
from src.log_utils import info, warn, error


from src.database_manager import save_prices_to_db, load_prices_from_db
from src.config import MAIN_DB_NAME, DATA_DIR
from src.indicators import calculate_price_change, ema, trend, calculate_annualized_metrics, calculate_extreme_closes, calculate_distance_highest_close

# The database name is now a constant imported from database_manager
DB_NAME = MAIN_DB_NAME

def load_all_prices() -> pd.DataFrame:
    """A wrapper to load data from the main database."""
    return load_prices_from_db(MAIN_DB_NAME)

@st.cache_data(ttl=3600)
# UPDATED SIGNATURE: make period, start, and end optional
def get_all_prices_cached(tickers: list, interval: str, cache_version_key=None, period: str = None, start: str = None, end: str = None) -> pd.DataFrame:
    """
    Fetches and caches all ticker data from yfinance and returns a single DataFrame.
    
    It accepts either a 'period' string OR 'start' and 'end' date strings.
    """
    info(f"Fetching data for {len(tickers)} tickers...")

    if not tickers:
        warn("No tickers provided for fetching.")
        return pd.DataFrame()

    # START OF LOGIC TO DETERMINE YFINANCE ARGUMENTS
    yfinance_kwargs = {
        'tickers': tickers,
        'interval': interval,
        'group_by': 'ticker',
        # Keep auto_adjust=False to maintain raw data columns just in case
        'auto_adjust': False, 
        'threads': True,
        'progress': False
    }

    if period and not start and not end:
        # Scenario 1: Preset period (e.g., '1y') is provided
        yfinance_kwargs['period'] = period
    elif start:
        # Scenario 2: Custom date(s) are provided
        yfinance_kwargs['start'] = start
        if end:
            yfinance_kwargs['end'] = end
        # Ensure 'period' is not passed if 'start' is used
        yfinance_kwargs.pop('period', None)
    else:
        # Default fallback (e.g., if no time constraint was specified)
        warn("No period or start date specified. Defaulting to '1y' period.")
        yfinance_kwargs['period'] = '1y'
    # END OF LOGIC TO DETERMINE YFINANCE ARGUMENTS

    try:
        # Use the dynamically created yfinance_kwargs dictionary to fetch price data
        data = yf.download(**yfinance_kwargs)
    except Exception as e:
        error(f"Error fetching data from yfinance: {e}")
        return pd.DataFrame()

    if data.empty:
        warn("No data returned from yfinance.")
        return pd.DataFrame()
    
    df_list = []
    
    # We will now standardize the column creation AFTER the data is in a list of DataFrames
    if isinstance(data.columns, pd.MultiIndex):
        # Multi-ticker case
        for ticker in tickers:
            if ticker in data.columns.get_level_values(0):
                # Ensure the column extraction logic is robust
                df = data[ticker].copy().reset_index()
                df['Ticker'] = ticker
                df_list.append(df)
    else:
        # Single-ticker case
        df = data.copy().reset_index()
        df['Ticker'] = tickers[0]
        df_list.append(df)
    
    if not df_list:
        warn("No data processed from fetched results. Returning an empty DataFrame.")
        return pd.DataFrame()

    combined_df = pd.concat(df_list, ignore_index=True)

    # Crucial Fix: Standardize the 'Date' or 'index' column to 'Datetime'
    if 'Date' in combined_df.columns:
        combined_df.rename(columns={'Date': 'Datetime'}, inplace=True)
    elif 'index' in combined_df.columns:
        combined_df.rename(columns={'index': 'Datetime'}, inplace=True)
    
    # Check if a 'Datetime' column now exists before proceeding
    if 'Datetime' in combined_df.columns:
        combined_df['Date'] = combined_df['Datetime'].dt.date
        combined_df['Time'] = combined_df['Datetime'].dt.time
        combined_df.drop(columns=['Datetime'], inplace=True)
        
        # FIX: Preserve the adjusted close price and ensure only one 'Close' column exists.
        if 'Adj Close' in combined_df.columns:
            # 1. Temporarily store the adjusted price.
            combined_df['Close_Adjusted_Temp'] = combined_df['Adj Close']
            
            # 2. Drop all redundant price columns returned by yfinance (raw Close, Adj Close, etc.)
            cols_to_drop = ['Open', 'High', 'Low', 'Volume', 'Close', 'Adj Close']
            combined_df.drop(columns=[col for col in cols_to_drop if col in combined_df.columns], inplace=True, errors='ignore')
            
            # 3. Rename the temporary column to the required 'Close' column.
            combined_df.rename(columns={'Close_Adjusted_Temp': 'Close'}, inplace=True)

        # --- NEW ROBUST DIVIDEND FETCHING LOGIC (Optimized for Speed) ---
        info(f"Fetching dividend history separately for {len(tickers)} tickers in parallel...")
        dividend_dfs = []
        
        def fetch_ticker_actions(ticker):
            """Helper function to fetch actions for a single ticker."""
            try:
                # Fetch full historical actions (Dividends and Splits)
                actions_df = yf.Ticker(ticker).actions
                
                # Filter for only positive dividend events
                if 'Dividends' in actions_df.columns and not actions_df.empty:
                    dividends_only = actions_df[['Dividends']].loc[actions_df['Dividends'] > 0]
                    dividends_only = dividends_only.reset_index()
                    dividends_only.rename(columns={'Date': 'Dividend_Date'}, inplace=True)
                    dividends_only['Ticker'] = ticker
                    return dividends_only
            except Exception as e:
                warn(f"Could not fetch actions for {ticker} concurrently: {e}")
            return None
        
        # Use ThreadPoolExecutor to fetch data concurrently
        with ThreadPoolExecutor(max_workers=min(10, len(tickers))) as executor:
            # Submit all fetch tasks
            futures = [executor.submit(fetch_ticker_actions, ticker) for ticker in tickers]
            
            # Process results as they complete
            for future in as_completed(futures):
                result_df = future.result()
                if result_df is not None:
                    dividend_dfs.append(result_df)

        if dividend_dfs:
            dividends_combined = pd.concat(dividend_dfs, ignore_index=True)
            # Standardize Dividend_Date to match main data's 'Date' format (date object)
            dividends_combined['Date'] = dividends_combined['Dividend_Date'].dt.date
            dividends_combined.drop(columns=['Dividend_Date'], inplace=True)
            
            # Merge dividends into the main combined_df using Ticker and Date
            combined_df = pd.merge(
                combined_df, 
                dividends_combined[['Ticker', 'Date', 'Dividends']], 
                on=['Ticker', 'Date'], 
                how='left'
            )
            info("Successfully merged dividend data.")
        else:
            info("No dividend data found via Ticker().actions for selected tickers.")

        # FINAL DIVIDEND CLEANUP
        # Ensure the 'Dividends' column exists (it might not if no data was merged)
        if 'Dividends' not in combined_df.columns:
             combined_df['Dividends'] = 0.0
             warn("No dividend data found in any format. Initializing 'Dividends' to 0.0.")
        
        # Fill NaNs (where no dividend was paid on a given day) with 0.
        combined_df['Dividends'] = combined_df['Dividends'].fillna(0).astype(float)
        
        # Log status
        dividend_sum = combined_df['Dividends'].sum()
        if dividend_sum == 0.0 and not combined_df.empty:
            warn(f"Total summed dividends across ALL data is 0.0. Please verify the period/tickers pay dividends.")
        else:
            info(f"SUCCESS: Total dividend payments detected: {dividend_sum:.2f}")
        # --- END OF NEW ROBUST DIVIDEND FETCHING LOGIC ---


        # Drop any remaining unnecessary columns (Open, High, Low, Volume)
        # Note: 'Close' must exist at this point.
        combined_df.drop(columns=[col for col in ['Open', 'High', 'Low', 'Volume'] if col in combined_df.columns and col != 'Dividends'], inplace=True, errors='ignore')

        
    else:
        # This case should now be impossible, but it's a good fail-safe
        error("The 'Datetime' column was not found after renaming. Data processing failed.")
        return pd.DataFrame()

    # Save the finalized DataFrame to the main dashboard database
    save_prices_to_db(combined_df, MAIN_DB_NAME)
    info("SUCCESS: Data fetched and saved to database.")

    # Return the combined DataFrame for use in the dashboard
    return combined_df          


@st.cache_data(show_spinner="Calculating indicators...")
def calculate_all_indicators(df_daily, fast_n, slow_n)-> pd.DataFrame:
    # Apply all calculation functions here
    # Ensure the DataFrame is sorted and indexed
    df_daily = df_daily.sort_values(['Ticker', 'Date'])

    # 1. Calculate Daily Return (Required for performance metrics)
    df_daily['Daily Return'] = df_daily.groupby('Ticker')['Close'].pct_change(fill_method=None)

    # 2. Calculate EMAs and Trend
    df_daily = calculate_price_change(df_daily)
    df_daily = trend(df_daily, fast_n, slow_n)
    df_daily = ema(df_daily, fast_n)
    
    # UPDATED: Call the new extreme price function
    df_daily = calculate_extreme_closes(df_daily) 
    # UPDATED: Call the new distance function
    df_daily = calculate_distance_highest_close(df_daily) 

    # 3. Calculate Annualized Metrics (uses the full data slice per ticker)
    # The 'Ticker' column is crucial here for the groupby in the metrics function.
    annual_metrics_df = calculate_annualized_metrics(df_daily[['Ticker', 'Date', 'Close', 'Daily Return']].copy())
    
    # 4. Merge the new performance metrics back into the main DataFrame
    # Note: Annual metrics are calculated on the whole period, so they only exist
    # for the last observation (the snapshot).
    # Use the 'Date' from the annual_metrics_df to join onto the main daily data
    # (Since annual_metrics_df only contains the final, latest date per ticker).
    df_daily = pd.merge(
        df_daily, 
        annual_metrics_df[['Ticker', 'Avg Return', 'Annualized Vol', 'Sharpe Ratio']],
        on='Ticker',
        how='left'
    )
    
    # 5. Return the enriched DataFrame
    return df_daily