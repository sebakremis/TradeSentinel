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