# src/sim_portfolio.py
import pandas as pd

def calculate_portfolio(selected_tickers, df_full_data, portfolio_size):
    """
    Calculates an equally weighted portfolio for the selected tickers,
    using the first available price from the lookback period to determine shares.
    
    Args:
        selected_tickers (list): List of ticker symbols selected by the user.
        df_full_data (pd.DataFrame): The full historical daily DataFrame (df_daily) 
                                     containing 'Ticker' and 'Close' prices.
        portfolio_size (float/int): The total amount of investment capital.
        
    Returns:
        list: A list of (Ticker, Shares) tuples.
    """
    if not selected_tickers:
        return []

    # 1. Filter the DataFrame to include only the selected tickers
    portfolio_df = df_full_data[df_full_data['Ticker'].isin(selected_tickers)].copy()

    # 2. Get the *first* price for each ticker in the lookback period
    # Group by Ticker and select the first 'Close' price (which corresponds to 
    # the oldest date fetched for the selected period).
    first_prices = portfolio_df.groupby('Ticker')['Close'].first().reset_index(name='Starting_Price')
    
    # Check if we have prices for all selected tickers (should match num_tickers)
    if first_prices.empty:
         return []
    
    # 3. Calculate investment per ticker
    num_tickers = len(first_prices)
    investment_per_ticker = portfolio_size / num_tickers
    
    # 4. Calculate shares for each ticker
    first_prices['Shares'] = round(investment_per_ticker / first_prices['Starting_Price'])
    
    # 5. Create the list of (Ticker, Shares) tuples
    portfolio_list = list(zip(first_prices['Ticker'], first_prices['Shares']))
    
    return portfolio_list

# Example usage:
# selected_tickers = ['AAPL', 'MSFT', 'GOOGL']
# df = pd.DataFrame({
# 'Ticker': ['AAPL', 'MSFT', 'GOOGL'],
# 'Close': [150.0, 250.0, 2800.0]
# })
# portfolio_size = 10000
# portfolio = calculate_portfolio(selected_tickers, df, portfolio_size)
# print(portfolio)  # Output: [('AAPL', 22.22222222222222), ('MSFT', 13.333333333333334), ('GOOGL', 3.5714285714285716)]
