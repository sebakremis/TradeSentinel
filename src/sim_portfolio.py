# src/sim_portfolio.py
import pandas as pd

def calculate_portfolio(selected_tickers, df, portfolio_size):
    """
    Calculates an equally weighted portfolio for the selected tickers
    and returns a list of (Ticker, Shares) tuples.
    """
    if not selected_tickers:
        return []

    # Filter the DataFrame to include only the selected tickers
    portfolio_df = df[df['Ticker'].isin(selected_tickers)].copy()
    
    # Calculate investment per ticker
    num_tickers = len(portfolio_df)
    investment_per_ticker = portfolio_size / num_tickers
    
    # Calculate shares for each ticker
    portfolio_df['Shares'] = round(investment_per_ticker / portfolio_df['Close'])
    
    # Create the list of (Ticker, Shares) tuples
    portfolio_list = list(zip(portfolio_df['Ticker'], portfolio_df['Shares']))
    
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
