# src/dashboard_manager.py
import streamlit as st
import pandas as pd
import duckdb

# Imports for concurrent processing
from src.log_utils import warn
from src.config import DATA_DIR, stocks_folder
from src.indicators import calculate_annualized_metrics, calculate_extreme_closes


def get_stock_data(tickers: list, interval: str, period: str = None, start: str = None, end: str = None) -> pd.DataFrame:
    """
    Fetches stock data directly from database into dashboard.
    It accepts either a 'period' string OR 'start' and 'end' date strings.
    Returns a DataFrame with stock data for the specified tickers and date range.
    Data interval is currently not used, but kept for future compatibility. It is assumed to be '1d'.
    """
    if not tickers:
        warn("No tickers provided for fetching.")
        return pd.DataFrame()
    
    if not start:
        # Calculate start date based on the period
        period_days_map = {
            '1mo': 30,
            '3mo': 90,
            '6mo': 180,
            '1y': 365,
            '2y': 730,
            '5y': 1825,
            'ytd': (pd.Timestamp.now() - pd.Timestamp(pd.Timestamp.now().year, 1, 1)).days,
        }
        days = period_days_map.get(period, 365)  # Default to 1 year if unknown period and start date
        start = (pd.Timestamp.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    if not end:
        end = pd.Timestamp.now().strftime('%Y-%m-%d')
    
    # Format tickers list for sql query
    tickers_sql = str(tuple(tickers)).replace(",)", ")")  # Handle single ticker case

    # Define path to metadata file
    metadata_path = f"{stocks_folder}/metadata.csv"

    # Load data from the database using duckdb
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

# test get_stock_data function
if __name__ == "__main__":
    tickers= ['GOOG', 'MSFT']
    df = get_stock_data(tickers, interval='1d', period='1y')
    print(df.info())
    print(df.head())



def calculate_all_indicators(df_daily)-> pd.DataFrame:
    # Ensure the DataFrame is sorted and indexed
    df_daily = df_daily.sort_values(['Ticker', 'Date'])

    # Calculate Daily Return (Required for performance metrics)
    df_daily['dailyReturn'] = df_daily.groupby('Ticker')['close'].pct_change(fill_method=None)
  
    # Call the extreme price function
    df_daily = calculate_extreme_closes(df_daily) 
    
    # Calculate Annualized Metrics (uses the full data slice per ticker)
    # The 'Ticker' column is crucial here for the groupby in the metrics function.
    annual_metrics_df = calculate_annualized_metrics(df_daily[['Ticker', 'Date', 'close', 'dailyReturn']].copy())
    
    # 4. Merge the new performance metrics back into the main DataFrame
    # Note: Annual metrics are calculated on the whole period, so they only exist
    # for the last observation (the snapshot).
    # Use the 'Date' from the annual_metrics_df to join onto the main daily data
    # (Since annual_metrics_df only contains the final, latest date per ticker).
    df_daily = pd.merge(
        df_daily, 
        annual_metrics_df[['Ticker', 'avgReturn', 'annualizedVol', 'sharpeRatio']],
        on='Ticker',
        how='left'
    )  
    
    # 5. Return the enriched DataFrame
    return df_daily

def dynamic_filtering(sorted_df: pd.DataFrame, DISPLAY_COLUMNS: list) -> pd.DataFrame:
    """
    Applies dynamic filtering to the DataFrame.
    Returns the filtered DataFrame.
    """
    excluded_columns = ['Ticker', 'close', 'startPrice', 'divPayout', 'forecastLow', 'forecastHigh', '52WeekHigh', '52WeekLow']
    filter_options = [col for col in DISPLAY_COLUMNS if col not in excluded_columns]
    with st.expander("🔎 Filter Data", expanded=False):
        # Create columns for the filter controls
        f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
        
        with f_col1:
            # Allow user to select which column to filter
            filter_column = st.selectbox("Filter by:", options=filter_options)

        # Logic: Check if selected column is Numeric or Text
        if filter_column in sorted_df.columns:
            is_numeric = pd.api.types.is_numeric_dtype(sorted_df[filter_column])
            
            # --- NUMERIC FILTERING ---
            if is_numeric:
                min_val = float(sorted_df[filter_column].min())
                max_val = float(sorted_df[filter_column].max())
                
                # Handle edge case where column might be empty or all NaNs
                if pd.isna(min_val): min_val = 0.0
                if pd.isna(max_val): max_val = 1.0
                
                with f_col2:
                    # Select condition type
                    filter_condition = st.selectbox("Condition", ["Range", "Greater than", "Less than"])
                
                with f_col3:
                    if filter_condition == "Range":
                        # Use a slider for range
                        val_range = st.slider(
                            f"Select range for {filter_column}",
                            min_value=min_val,
                            max_value=max_val,
                            value=(min_val, max_val)
                        )
                        # Apply Filter
                        sorted_df = sorted_df[
                            (sorted_df[filter_column] >= val_range[0]) & 
                            (sorted_df[filter_column] <= val_range[1])
                        ]
                    elif filter_condition == "Greater than":
                        val = st.number_input(f"Value for {filter_column}", value=min_val)
                        sorted_df = sorted_df[sorted_df[filter_column] >= val]
                    elif filter_condition == "Less than":
                        val = st.number_input(f"Value for {filter_column}", value=max_val)
                        sorted_df = sorted_df[sorted_df[filter_column] <= val]

            # --- TEXT FILTERING ---
            else:
                unique_values = sorted_df[filter_column].dropna().unique().tolist()
                
                # Use Multiselect if there are few categories (like Sector), otherwise Text Search
                if len(unique_values) < 20:
                    with f_col3:
                        selected_items = st.multiselect(
                            f"Select {filter_column}", 
                            options=unique_values, 
                            default=unique_values
                        )
                        # Apply Filter
                        sorted_df = sorted_df[sorted_df[filter_column].isin(selected_items)]
                else:
                    with f_col3:
                        search_text = st.text_input(f"Search inside {filter_column}", "")
                        # Apply Filter
                        if search_text:
                            sorted_df = sorted_df[
                                sorted_df[filter_column].astype(str).str.contains(search_text, case=False, na=False)
                            ]
    return sorted_df