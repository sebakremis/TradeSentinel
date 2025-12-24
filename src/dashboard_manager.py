# src/dashboard_manager.py
import streamlit as st
import pandas as pd
import duckdb

from src.log_utils import warn
from src.config import DATA_DIR, stocks_folder
from src.indicators import calculate_annualized_metrics, distance_from_ema

def get_stock_data(tickers: list, interval: str, period: str = None, start: str = None, end: str = None) -> pd.DataFrame:
    """
    Fetches stock data directly from database into dashboard.
    """
    if not tickers:
        warn("No tickers provided for fetching.")
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
  
    # 2. Calculate Distance to EMA 50
    df_daily = distance_from_ema(df_daily, 50)
    
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