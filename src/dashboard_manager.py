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