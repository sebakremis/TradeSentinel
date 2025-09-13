# src/pnl_calculator.py

import pandas as pd
from typing import Union


def calculate_pnl(
    positions: pd.DataFrame,
    close_prices: Union[pd.Series, pd.DataFrame]
) -> pd.DataFrame:
    """
    Calculate mark-to-market Profit and Loss (PnL) for each position.

    This function takes a DataFrame of positions and a set of market prices,
    then computes the current value and PnL for each instrument.

    Args:
        positions (pd.DataFrame):
            Must contain the following columns:
                - 'Ticker' (str): Instrument ticker symbol
                - 'Quantity' (float/int): Number of units held
                - 'EntryPrice' (float): Price at which the position was opened
        close_prices (pd.Series or pd.DataFrame):
            - If DataFrame: last row per ticker is treated as the current price
            - If Series: index should be ticker symbols, values are current prices

    Returns:
        pd.DataFrame:
            Original positions DataFrame with added columns:
                - 'CurrentPrice': Latest market price for the ticker
                - 'PnL': Mark-to-market profit or loss
                - 'PositionValue': Current market value of the position

    Raises:
        ValueError: If `close_prices` is empty.
    """
    # Guard clause: prevent calculation if no prices are available
    if close_prices is None or close_prices.empty:
        raise ValueError("No price data available — cannot calculate PnL.")

    # Get the latest available prices
    if isinstance(close_prices, pd.DataFrame):
        latest = close_prices.ffill().iloc[-1]  # forward-fill missing values
    else:
        latest = close_prices

    # Copy to avoid modifying the original DataFrame
    positions = positions.copy()

    # Map current prices to tickers
    positions['CurrentPrice'] = positions['Ticker'].map(latest.to_dict())

    # Calculate PnL and position value
    positions['PnL'] = (positions['CurrentPrice'] - positions['EntryPrice']) * positions['Quantity']
    positions['PositionValue'] = positions['CurrentPrice'] * positions['Quantity']

    return positions


def main():
    """
    Example usage of calculate_pnl().

    This function:
    1. Creates a sample positions DataFrame
    2. Fetches market data using get_market_data() from data_fetch.py
    3. Calculates PnL
    4. Prints the results
    """
    from data_fetch import get_market_data  # Local import to avoid circular dependency

    # Example positions
    positions_df = pd.DataFrame({
        'Ticker': ['AAPL', 'MSFT'],
        'Quantity': [50, 30],
        'EntryPrice': [150.00, 280.00]
    })

    # Fetch latest prices
    prices_df = get_market_data(['AAPL', 'MSFT'], interval="1m", period="1d")

    # Calculate PnL
    try:
        pnl_df = calculate_pnl(positions_df, prices_df)
        print(pnl_df)
        print(f"Total PnL: {pnl_df['PnL'].sum():.2f}")
    except ValueError as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()



