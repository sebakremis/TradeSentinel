import pandas as pd

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
    df['Change %'] = df.groupby('Ticker')['Close'].pct_change() * 100

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
    Determines the trend based on a fast and slow EMA crossover.

    The trend is classified as 'long', 'short', or 'no trend' based on the
    relative positions of the last price, fast EMA, and slow EMA.

    Args:
        df (pd.DataFrame): The input DataFrame containing 'Close' and 'Ticker'
                           columns.
        fast_n (int): The period for the fast EMA.
        slow_n (int): The period for the slow EMA.
        price_col (str): The column to use for the price (default: 'Close').

    Returns:
        pd.DataFrame: The DataFrame with a new 'Trend' column.
    """
    # Calculate the fast and slow EMAs and add them to the DataFrame
    df = ema(df, fast_n)
    df = ema(df, slow_n)

    # Get the column names for the EMAs
    fast_ema_col = f'EMA_{fast_n}'
    slow_ema_col = f'EMA_{slow_n}'

    # Define the conditions for the trend
    long_condition = (df[price_col] > df[slow_ema_col]) & (df[fast_ema_col] > df[slow_ema_col])
    short_condition = (df[price_col] < df[slow_ema_col]) & (df[fast_ema_col] < df[slow_ema_col])
    
    # Use np.select for efficient conditional assignment
    import numpy as np
    conditions = [long_condition, short_condition]
    choices = ['long', 'short']
    df['Trend'] = np.select(conditions, choices, default='no trend')

    return df