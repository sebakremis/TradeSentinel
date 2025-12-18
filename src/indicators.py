# src/indicators.py
import pandas as pd
import numpy as np

def distance_from_ema(df: pd.DataFrame)->pd.DataFrame:
    df = df.sort_values(['Ticker', 'Date'])
    df['Distance_Ema20'] = ((df['close']-df['EMA_20'])/ df['EMA_20'])*100
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
    df['change'] = df.groupby('Ticker')['close'].diff()
    df['change%'] = df.groupby('Ticker')['close'].pct_change(fill_method=None) * 100

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
    df[ema_column_name] = df.groupby('Ticker')['close'].transform(
        lambda x: x.ewm(span=n, adjust=False).mean()
    )
    return df

def trend(df: pd.DataFrame, fast_n: int = 20, slow_n: int = 50, price_col: str = 'close') -> pd.DataFrame:
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
    if 'close' not in df.columns or 'Ticker' not in df.columns:
        raise ValueError("DataFrame must contain 'close' and 'Ticker' columns.")
        
    df = df.sort_values(['Ticker', 'Date'])
    
    # Calculate the rolling highest high for each ticker
    df['Highest Close'] = df.groupby('Ticker')['close'].transform(
        lambda x: x.shift(1).rolling(window=lookback, min_periods=1).max()
    )
    
    return df

def distance_highest_close(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the percent difference between the Close price and the
    pre-calculated Highest Close value.

    Args:
        df (pd.DataFrame): The DataFrame with 'close' and 'highestClose' columns.

    Returns:
        pd.DataFrame: The DataFrame with a new 'distanceHC' column.
    """
    if 'close' not in df.columns or 'highestClose' not in df.columns:
        raise ValueError("DataFrame must contain 'close' and 'highestClose' columns.")
        
    # Calculate the percent difference using the numerical formula
    df['distanceHC'] = ((df['close'] - df['highestClose']) / df['highestClose']) * 100
    
    return df

ANNUAL_TRADING_DAYS = 252 # Standard constant for annualization
annualized_risk_free_rate = 0.02 # 2% assumed RFR


def calculate_annualized_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the annualized average return, volatility, and Sharpe Ratio 
    based on the entire lookback period of the input DataFrame (per ticker).

    Args:
        df (pd.DataFrame): The input DataFrame, containing daily data for multiple 
                           tickers, with a 'Daily Return' column.
                           
    Returns:
        pd.DataFrame: A DataFrame containing one row per ticker with the latest 
                      calculated 'Avg Return', 'Annualized Vol', and 'Sharpe Ratio'.
    """
    
    # 1. Define Annualization Constants
    
    
    # 2. Define the aggregation logic for each Ticker
    def aggregate_metrics(group):
        """Calculates single-period annualized metrics for one ticker's data."""
        returns = group['dailyReturn'].dropna()
        N = len(returns)
        
        if N < 5: # Need a minimum number of observations for meaningful stats
            return pd.Series({'avgReturn': np.nan, 'annualizedVol': np.nan, 'sharpeRatio': np.nan})

        # --- A. Annualized Volatility (Risk) ---
        # Volatility scales by the square root of time
        daily_vol = returns.std()
        annualized_vol = daily_vol * np.sqrt(ANNUAL_TRADING_DAYS)
        
        # --- B. Annualized Return (Geometric Compounded Return) ---
        # Total compounded return = Product(1 + r_i) - 1
        total_return = (1 + returns).prod() - 1 
        
        # Annualization factor: (Annual periods) / (Number of periods in the lookback)
        annualization_factor = ANNUAL_TRADING_DAYS / N 
        
        # Geometric Annualized Return: (1 + R_total)^(Factor) - 1
        # Use abs() to prevent issues with negative base and fractional exponent
        annualized_return = (1 + total_return) ** annualization_factor - 1
        
        # --- C. Sharpe Ratio ---
        sharpe_ratio = (annualized_return - annualized_risk_free_rate) / annualized_vol if annualized_vol != 0 else np.nan

        return pd.Series({
            # Store as percentage for easier formatting later (100 is applied in _format_final_df)
            'avgReturn': annualized_return * 100,
            'annualizedVol': annualized_vol * 100,
            'sharpeRatio': sharpe_ratio
        })

    # Ensure Daily Return is calculated before aggregation
    if 'dailyReturn' not in df.columns:
        df['dailyReturn'] = df.groupby('Ticker')['close'].pct_change()

    # Apply the aggregation logic
    annual_metrics_df = df.groupby('Ticker').apply(aggregate_metrics, include_groups=False).reset_index()

    # Get the latest date for each ticker for the final merge
    latest_dates = df.groupby('Ticker').tail(1)[['Ticker', 'Date']].reset_index(drop=True)
    
    # Merge the calculated metrics onto the latest snapshot
    final_metrics_df = pd.merge(latest_dates, annual_metrics_df, on='Ticker')
    
    return final_metrics_df

def calculate_extreme_closes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the Highest and Lowest Closing Price for the entire lookback period 
    and merges the results onto every row of the input DataFrame (per Ticker).

    Args:
        df (pd.DataFrame): The full historical daily DataFrame, including 'Ticker' and 'Close'.

    Returns:
        pd.DataFrame: The original DataFrame with the new 'Highest Close' and 'Lowest Close' columns.
    """
    
    # Calculate Highest/Lowest Close for the entire lookback period per Ticker
    extreme_prices = df.groupby('Ticker')['close'].agg(
        highest_close='max',
        lowest_close='min'
    ).reset_index()
    
    # Merge these values back onto the main DataFrame using 'Ticker'
    df = pd.merge(
        df,
        extreme_prices,
        on='Ticker',
        how='left'
    )
    
    # Rename columns to match desired output
    df.rename(columns={
        'highest_close': 'highestClose',
        'lowest_close': 'lowestClose'
    }, inplace=True)
    
    return df

def calculate_distance_highest_close(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the percentage distance from the current price to the Highest Close.
    
    NOTE: Assumes 'Highest Close' has already been calculated and merged onto df.

    Args:
        df (pd.DataFrame): The full historical daily DataFrame, with 'Close' and 'Highest Close'.

    Returns:
        pd.DataFrame: The original DataFrame with the new 'Distance HC' column.
    """
    
    # Formula: (Current Close - Highest Close) / Highest Close * 100
    # The result will be negative or zero.
    df['Distance HC'] = (
        (df['close'] - df['highestClose']) / df['highestClose']
    ) * 100
    
    return df


