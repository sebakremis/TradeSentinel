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

def higher_high(df: pd.DataFrame, lookback: int = 10) -> pd.DataFrame:
    """
    Calculates the higher high for each Ticker over a specified lookback period.

    Args:
        df (pd.DataFrame): The input DataFrame with 'Close', 'Date', and 'Ticker' columns.
        lookback (int): The number of periods to look back for the higher high.

    Returns:
        pd.DataFrame: The DataFrame with a new 'HigherHigh' column.
    """
    if 'Close' not in df.columns or 'Ticker' not in df.columns:
        raise ValueError("DataFrame must contain 'Close' and 'Ticker' columns.")
        
    df = df.sort_values(['Ticker', 'Date'])
    
    # Calculate the rolling higher high for each ticker
    df['HigherHigh'] = df.groupby('Ticker')['Close'].transform(
        lambda x: x.shift(1).rolling(window=lookback, min_periods=1).max()
    )
    
    return df

def distance_higher_high(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the percent difference between the Close price and the
    pre-calculated Higher High value.

    Args:
        df (pd.DataFrame): The DataFrame with 'Close' and 'HigherHigh' columns.

    Returns:
        pd.DataFrame: The DataFrame with a new 'Percent_Diff_From_HH' column.
    """
    if 'Close' not in df.columns or 'HigherHigh' not in df.columns:
        raise ValueError("DataFrame must contain 'Close' and 'HigherHigh' columns.")
        
    # Calculate the percent difference using the numerical formula
    df['Distance'] = ((df['Close'] - df['HigherHigh']) / df['HigherHigh']) * 100
    
    return df