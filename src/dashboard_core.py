"""
src/dashboard_core.py

This module unifies the responsibilities previously handled by `dashboard_manager.py`
and `tickers_manager.py` into a single, cohesive core for dashboard orchestration.

Key responsibilities:
    - Central coordination of dashboard logic, ensuring consistent behavior across
      multiple views and pages.
    - Management of ticker-related operations (loading, updating, validating, and
      formatting market symbols) as part of the dashboard workflow.
    - Integration of data pipelines with display components, acting as the bridge
      between analytics modules (e.g., portfolio calculations, indicators, forecasts)
      and the user interface layer.
    - Providing reusable functions and abstractions that simplify dashboard
      development, reduce duplication, and enforce a clear separation of concerns.

Design notes:
    - Functions in this module are intended to be **core orchestration utilities**,
      not page-specific rendering logic (which remains in `dashboard_display.py` or
      individual page modules).
    - By consolidating managers into a single module, the project gains improved
      modularity, easier maintenance, and a clearer entry point for dashboard-related
      functionality.
    - Naming conventions should reflect orchestration responsibilities, e.g.,
      `init_dashboard()`, `update_tickers()`, `sync_data_sources()`.

In short, `dashboard_core.py` serves as the backbone of the TradeSentinel dashboard,
linking ticker management with dashboard state and ensuring a unified, maintainable
workflow.
"""
import streamlit as st
import pandas as pd
import duckdb
from pathlib import Path
import yfinance as yf
from src.config import followed_tickers_file, DATA_DIR, stocks_folder
from src.analytics import calculate_annualized_metrics, distance_from_ema

# Dashboard manager

def get_stock_data(tickers: list, interval: str, period: str = None, start: str = None, end: str = None) -> pd.DataFrame:
    """
    Fetches stock data directly from database into dashboard.
    """
    if not tickers:
        print("No tickers provided for fetching.")
        return pd.DataFrame()
    
    if not start:
        period_days_map = {
            '1mo': 30, '3mo': 90, '6mo': 180, '1y': 365,
            '2y': 730, '5y': 1825,
            'ytd': (pd.Timestamp.now() - pd.Timestamp(pd.Timestamp.now().year, 1, 1)).days,
        }
        days = period_days_map.get(period, 365)
        start = (pd.Timestamp.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    if not end:
        end = pd.Timestamp.now().strftime('%Y-%m-%d')
    
    tickers_sql = str(tuple(tickers)).replace(",)", ")")
    metadata_path = f"{stocks_folder}/metadata.csv"

    query = rf"""
        WITH raw_prices AS (
            SELECT *,
            regexp_extract(filename, '[\\\\/]([^\\\\/]+)\.parquet$', 1) AS Ticker
            FROM read_parquet('{stocks_folder}/prices/*.parquet')
        ),
        clean_metadata AS (
            SELECT * FROM read_csv_auto('{metadata_path}')
            WHERE Ticker IS NOT NULL AND Ticker != ''
        )
        SELECT p.*,
        m.* EXCLUDE(Ticker)
        FROM raw_prices AS p
        LEFT JOIN clean_metadata AS m
        ON p.Ticker = m.Ticker
        WHERE p.Ticker IN {tickers_sql}
          AND p.Date BETWEEN '{start}' AND '{end}'
        ORDER BY p.Ticker, p.Date DESC
    """
    df = duckdb.query(query).to_df()
    return df

def calculate_all_indicators(df_daily) -> pd.DataFrame:
    # Ensure the DataFrame is sorted
    df_daily = df_daily.sort_values(['Ticker', 'Date'])

    # 1. Calculate Daily Return
    df_daily['dailyReturn'] = df_daily.groupby('Ticker')['close'].pct_change(fill_method=None)
  
    # 2. Calculate Distance to EMA 20
    df_daily = distance_from_ema(df_daily, 20)
    
    # 3. Calculate Annualized Metrics
    annual_metrics_df = calculate_annualized_metrics(df_daily[['Ticker', 'Date', 'close', 'dailyReturn']].copy())
    
    # 4. Merge metrics back
    df_daily = pd.merge(
        df_daily, 
        annual_metrics_df[['Ticker', 'avgReturn', 'annualizedVol', 'sharpeRatio']],
        on='Ticker',
        how='left'
    )  
    
    return df_daily

def dynamic_filtering(sorted_df: pd.DataFrame, DISPLAY_COLUMNS: list) -> pd.DataFrame:
    """
    Applies dynamic filtering to the DataFrame.
    """
    # Added EMA_50 to excluded columns for filters if you don't want it in the dropdown, 
    # remove it from this list if you DO want to filter by EMA.
    excluded_columns = ['Ticker', 'close', 'startPrice', 'divPayout', 'forecastLow', 'forecastHigh', '52WeekHigh', '52WeekLow']
    filter_options = [col for col in DISPLAY_COLUMNS if col not in excluded_columns]
    
    with st.expander("🔎 Filter Data", expanded=False):
        f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
        
        with f_col1:
            filter_column = st.selectbox("Filter by:", options=filter_options)

        if filter_column in sorted_df.columns:
            is_numeric = pd.api.types.is_numeric_dtype(sorted_df[filter_column])
            
            if is_numeric:
                min_val = float(sorted_df[filter_column].min())
                max_val = float(sorted_df[filter_column].max())
                
                if pd.isna(min_val): min_val = 0.0
                if pd.isna(max_val): max_val = 1.0
                
                with f_col2:
                    filter_condition = st.selectbox("Condition", ["Range", "Greater than", "Less than"])
                
                with f_col3:
                    if filter_condition == "Range":
                        val_range = st.slider(f"Range {filter_column}", min_val, max_val, (min_val, max_val))
                        sorted_df = sorted_df[(sorted_df[filter_column] >= val_range[0]) & (sorted_df[filter_column] <= val_range[1])]
                    elif filter_condition == "Greater than":
                        val = st.number_input(f"Value for {filter_column}", value=min_val)
                        sorted_df = sorted_df[sorted_df[filter_column] >= val]
                    elif filter_condition == "Less than":
                        val = st.number_input(f"Value for {filter_column}", value=max_val)
                        sorted_df = sorted_df[sorted_df[filter_column] <= val]

            else: # Text Filtering
                unique_values = sorted_df[filter_column].dropna().unique().tolist()
                if len(unique_values) < 20:
                    with f_col3:
                        selected_items = st.multiselect(f"Select {filter_column}", options=unique_values, default=unique_values)
                        sorted_df = sorted_df[sorted_df[filter_column].isin(selected_items)]
                else:
                    with f_col3:
                        search_text = st.text_input(f"Search {filter_column}", "")
                        if search_text:
                            sorted_df = sorted_df[sorted_df[filter_column].astype(str).str.contains(search_text, case=False, na=False)]
    return sorted_df


# Tickers manager

# Path to the followed tickers CSV file
filepath = followed_tickers_file

# Define a custom exception for better error handling
class TickerValidationError(Exception):
    """Custom exception for invalid or missing ticker data."""
    pass

def load_tickers(tickers_path: Path = filepath) -> pd.DataFrame:
    """
    Loads tickers from a single CSV file.
    Loads followed tickers by default.
    Returns a DataFrame with a 'Ticker' column.
    """   
    filename = tickers_path.name
    tickers_df = pd.DataFrame()

    try:
        tickers_df = pd.read_csv(tickers_path)
    except FileNotFoundError:
        st.error(f"❌ Error loading tickers: File not found at {tickers_path}")
        return pd.DataFrame(columns=['Ticker'])
    except Exception as e:
        st.error(f"❌ Error loading tickers: {e}")
        return pd.DataFrame(columns=['Ticker'])

    if tickers_df.empty or 'Ticker' not in tickers_df.columns:
        st.warning(f"⚠️ No tickers found in {filename}.")
        return pd.DataFrame(columns=['Ticker'])
        
    return tickers_df

def save_followed_tickers(tickers: pd.DataFrame) -> None:
    """
    Save tickers to CSV.
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
        tickers.to_csv(filepath, index=False)
    except Exception as e:
        st.error(f"❌ Error saving tickers: {e}")
        return

def get_followed_tickers():
    """
    Reads the CSV file for Followed Tickers.
    Returns the DataFrame.
    """
    try:
        followed_tickers_df = pd.read_csv(filepath)
    except FileNotFoundError:
        followed_tickers_df = pd.DataFrame(columns=['Ticker'])

    return followed_tickers_df

def add_ticker(ticker: str) -> None:
    """Add a ticker after fetching and validating its sector."""
    # Get the DataFrame from session state
    tickers_df = get_followed_tickers()
    
    # Check for duplicates
    if ticker in tickers_df['Ticker'].values:
        raise TickerValidationError(f"Ticker '{ticker}' is already being followed.")
    
    # Fetch data from Yahoo Finance
    yf_ticker = yf.Ticker(ticker)
    info = yf_ticker.info

    # Validate the ticker
    if not info:
        raise TickerValidationError(f"Ticker '{ticker}' is not valid.")
         
    # Save the updated DataFrame to disk
    new_row = pd.DataFrame({'Ticker': [ticker]})
    expanded_df = pd.concat([tickers_df, new_row], ignore_index=True)
    save_followed_tickers(expanded_df)
    
def remove_ticker(ticker: str) -> None:
    """Removes a ticker if it is already present."""
    # Get the DataFrame from session state
    tickers_df = get_followed_tickers()
    
    # Check if the ticker exists in the list
    if ticker not in tickers_df['Ticker'].values:
        raise TickerValidationError(f"Ticker '{ticker}' is not currently being followed.")
    
    # Remove the ticker row using boolean indexing and update session state
    reduced_df = tickers_df[tickers_df['Ticker'] != ticker].reset_index(drop=True)
    
    # Save the updated DataFrame to disk
    save_followed_tickers(reduced_df)

@st.dialog("Removing tickers from watchlist")
def confirm_unfollow_dialog(tickers_to_remove:list):
    """
    Displays a confirmation dialog before unfollowing tickers.
    """
    st.write(f"Unfollowing tickers: **{', '.join(tickers_to_remove)}**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Confirm Unfollow"):
            for ticker in tickers_to_remove:
                try:
                    remove_ticker(ticker)
                except TickerValidationError as e:
                    st.error(f"❌ {e}")
            st.rerun()  # Refresh the app to reflect changes
    with col2:
        if st.button("Cancel"):
            st.rerun()  # Refresh the app to reflect changes

@st.dialog("Adding tickers to watchlist")
def confirm_follow_dialog(tickers_to_add:list):
    """
    Displays a confirmation dialog before adding tickers to follow.
    """
    st.write(f"Adding tickers: **{', '.join(tickers_to_add)}**")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Confirm & switch to watchlist page"):
            for ticker in tickers_to_add:
                try:
                    add_ticker(ticker)
                except TickerValidationError as e:
                    st.error(f"❌ {e}")
            st.switch_page("pages/02_watchlist.py")
    with col2:
        if st.button("Confirm & stay on main page"):
            for ticker in tickers_to_add:
                try:
                    add_ticker(ticker)
                except TickerValidationError as e:
                    st.error(f"❌ {e}")
            st.rerun()  # Refresh the app to reflect changes
    with col3:
        if st.button("Cancel"):
            st.rerun()