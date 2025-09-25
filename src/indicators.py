# src/indicators.py
import pandas as pd
import numpy as np

def distance_from_ema(df: pd.DataFrame)->pd.DataFrame:
    df = df.sort_values(['Ticker', 'Date'])
    df['Distance_Ema20'] = ((df['Close']-df['EMA_20'])/ df['EMA_20'])*100
    return df
    

def calculate_price_change(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the 'Change' and 'Change %' columns for a DataFrame.

    This function is designed to work with a DataFrame that has a 'Close'
    column and a 'Ticker' column. It calculates the difference and percentage
    change from the previous close price for each ticker.

    Args:
        df (pd.DataFrame): The input DataFrame containing 'Close' and 'Ticker'
                          columns.

    Returns:
        pd.DataFrame: The DataFrame with 'Change' and 'Change %' columns added.
    """
    # Ensure the DataFrame is sorted to correctly calculate change
    df = df.sort_values(['Ticker', 'Date'])

    # Group by ticker and calculate the difference and percentage change
    df['Change'] = df.groupby('Ticker')['Close'].diff()
    df['Change %'] = df.groupby('Ticker')['Close'].pct_change(fill_method=None) * 100

    return df

def ema(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """
    Calculates the Exponential Moving Average (EMA) for each ticker.

    The EMA is calculated on the 'Close' column for a specified period 'n'.
    The function groups the data by 'Ticker' to ensure the EMA is
    calculated independently for each stock.

    Args:
        df (pd.DataFrame): The input DataFrame containing 'Close' and 'Ticker'
                          columns.
        n (int): The period (window size) for the EMA calculation.

    Returns:
        pd.DataFrame: The DataFrame with a new column for the EMA.
    """
    # Ensure the DataFrame is sorted by Ticker and Date
    df = df.sort_values(['Ticker', 'Date'])

    # Group by Ticker and apply the EMA calculation
    ema_column_name = f'EMA_{n}'
    df[ema_column_name] = df.groupby('Ticker')['Close'].transform(
        lambda x: x.ewm(span=n, adjust=False).mean()
    )
    return df

def trend(df: pd.DataFrame, fast_n: int = 20, slow_n: int = 50, price_col: str = 'Close') -> pd.DataFrame:
    """
    Determines the trend based on a three-EMA crossover system.

    The trend is classified as 'long', 'short', or 'neutral' based on the
    relative positions of the fast, mid, and slow EMAs.

    Args:
        df (pd.DataFrame): The input DataFrame containing 'Close' and 'Ticker'
                           columns.
        fast_n (int): The period for the fast EMA.
        mid_n (int): The period for the mid EMA.
        slow_n (int): The period for the slow EMA.
        price_col (str): The column to use for the price (default: 'Close').

    Returns:
        pd.DataFrame: The DataFrame with a new 'Trend' column.
    """
    # Calculate the fast, mid, and slow EMAs using the provided ema function
    df = ema(df, fast_n)
    df = ema(df, slow_n)

    # Get the column names for the EMAs
    fast_ema_col = f'EMA_{fast_n}'
    slow_ema_col = f'EMA_{slow_n}'

    # Define the conditions for the trend based on the three EMAs
    # Long: 
    long_condition = (df[fast_ema_col] > df[slow_ema_col]) & (df[price_col] > df[slow_ema_col])
    # Short: 
    short_condition = (df[fast_ema_col] < df[slow_ema_col]) & (df[price_col] < df[slow_ema_col])
    
    # Use np.select for efficient conditional assignment
    
    conditions = [long_condition, short_condition]
    choices = ['long', 'short']
    df['Trend'] = np.select(conditions, choices, default='neutral')

    return df

def highest_close(df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
    """
    Calculates the highest high for each Ticker over a specified lookback period.

    Args:
        df (pd.DataFrame): The input DataFrame with 'Close', 'Date', and 'Ticker' columns.
        lookback (int): The number of periods to look back for the highest high.

    Returns:
        pd.DataFrame: The DataFrame with a new 'Highest Close' column.
    """
    if 'Close' not in df.columns or 'Ticker' not in df.columns:
        raise ValueError("DataFrame must contain 'Close' and 'Ticker' columns.")
        
    df = df.sort_values(['Ticker', 'Date'])
    
    # Calculate the rolling highest high for each ticker
    df['Highest Close'] = df.groupby('Ticker')['Close'].transform(
        lambda x: x.shift(1).rolling(window=lookback, min_periods=1).max()
    )
    
    return df

def distance_highest_close(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the percent difference between the Close price and the
    pre-calculated Highest Close value.

    Args:
        df (pd.DataFrame): The DataFrame with 'Close' and 'Highest Close' columns.

    Returns:
        pd.DataFrame: The DataFrame with a new 'Percent_Diff_From_HH' column.
    """
    if 'Close' not in df.columns or 'Highest Close' not in df.columns:
        raise ValueError("DataFrame must contain 'Close' and 'Highest Close' columns.")
        
    # Calculate the percent difference using the numerical formula
    df['Distance'] = ((df['Close'] - df['Highest Close']) / df['Highest Close']) * 100
    
    return df

def annualized_metrics(df: pd.DataFrame, col: str = 'Change %', n_days: int = 200) -> pd.DataFrame:
    """
    Calculates the annualized average and volatility of a specified column.

    Args:
        df (pd.DataFrame): The input DataFrame, expected to have 'Ticker' and a 'Date' index.
        col (str): The name of the column to calculate volatility for. Default is 'Change %'.
        n_days (int): The number of days to use for the rolling window. Default is 200.

    Returns:
        pd.DataFrame: The original DataFrame with the new 'Annualized Avg' and 'Annualized Vol' columns.
    """
    df_copy = df.copy()

    # Calculate rolling average and volatility for each ticker using transform
    df_copy['Annualized Avg'] = df_copy.groupby('Ticker')[col].transform(lambda x: x.rolling(window=n_days).mean()) * 252
    
    # Calculate rolling standard deviation (volatility) and then annualize it
    df_copy['Annualized Vol'] = df_copy.groupby('Ticker')[col].transform(lambda x: x.rolling(window=n_days).std()) * np.sqrt(252)

    return df_copy