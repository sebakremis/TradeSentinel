"""
src/analytics.py

This module consolidates the functionality previously distributed across
`portfolio_calculations.py`, `indicators.py`, `price_forecast.py`, and `metrics.py`
into a unified analytics layer for TradeSentinel.

Key responsibilities:
    - Portfolio calculations:
        Provides functions for risk/return analysis, asset allocation metrics,
        and benchmark comparisons.
    - Technical indicators:
        Implements reusable indicator functions (e.g., moving averages, RSI,
        Bollinger Bands) for market analysis.
    - Price forecasting:
        Contains models and utilities for projecting asset prices and trends,
        including statistical and machine learning approaches.
    - Performance metrics:
        Computes evaluation metrics such as Sharpe ratio, volatility, drawdown,
        and other measures of portfolio and model performance.

Design notes:
    - Functions in this module follow a **functional, reusable design** so they
      can be imported across dashboards, pipelines, and notebooks.
    - By merging separate calculation modules into one, the project gains
      consistency, reduces duplication, and provides a single entry point for
      analytics-related functionality.
    - Naming conventions should reflect analytical scope, e.g.,
      `calculate_sharpe_ratio()`, `forecast_prices()`, `compute_rsi()`.

In short, `analytics.py` serves as the analytical backbone of TradeSentinel,
bringing together portfolio analysis, indicators, forecasting, and metrics into
a cohesive, maintainable module.
"""

import pandas as pd
import numpy as np
import streamlit as st
from src.config import (
    RISK_FREE_RATE, ANNUAL_TRADING_DAYS, CONFIDENCE_LEVEL, 
    FORECAST_HORIZON, N_SIMS, EMA_PERIOD, BENCHMARK_INDEX
)

# --- Portfolio Calculations ---

def calculate_pnl_data(prices: dict, quantities: dict) -> pd.DataFrame:
    """Calculates PnL, Dividends, and position snapshot data per ticker."""
    pnl_data = []
    
    for ticker, df in prices.items():
        if df is not None and not df.empty:
            try:
                # 1. Get Prices
                start = df["close"].iloc[0]
                end = df["close"].iloc[-1]
                
                # Safe conversion for single values
                if hasattr(start, "item"): start = start.item()
                if hasattr(end, "item"): end = end.item()

                qty = quantities.get(ticker, 0)
                
                # 2. Calculate Price PnL (Capital Gains)
                price_pnl = (end - start) * qty
                
                # 3. Calculate Dividends
                if 'dividends' in df.columns:
                    div_per_share = df['dividends'].sum()
                else:
                    div_per_share = 0.0
                
                total_div_payout = div_per_share * qty

                # 4. Calculate Totals and Metadata
                position_value = end * qty
                total_return = price_pnl + total_div_payout
                pct_change = ((end - start) / start) * 100 if start != 0 else 0.0
                
                sector = df["sector"].iloc[0] if "sector" in df.columns else "Unknown"

                pnl_data.append({
                    "Ticker": ticker,
                    "sector": sector,
                    "Quantity": qty,
                    "Start Price": start,
                    "End Price": end,
                    "PnL ($)": price_pnl,          # Price appreciation only
                    "Dividends ($)": total_div_payout, # Dividends payout
                    "Total Return ($)": total_return,  # Price PnL + Dividends
                    "Change (%)": pct_change,
                    "Position Value ($)": position_value
                })
            except Exception as e:
                print(f"{ticker}: Error calculating PnL — {e}")

    return pd.DataFrame(pnl_data) if pnl_data else pd.DataFrame()

def prepare_pnl_time_series(prices: dict, quantities: dict) -> pd.DataFrame:
    """Processes raw price data into a combined DataFrame for time series charting and export."""
    pnl_time_data = []
    
    for ticker, df in prices.items():
        if df is not None and not df.empty:
            try:
                tmp = df.copy()

                # Ensure datetime index
                if not isinstance(tmp.index, pd.DatetimeIndex):
                    tmp.index = pd.to_datetime(tmp.index)
                
                qty = quantities.get(ticker, 0)
                tmp["Quantity"] = qty
                tmp["Price"] = tmp["close"]
                
                # Standard Metrics
                tmp["Position Value ($)"] = tmp["Price"] * tmp["Quantity"]
                tmp["PnL"] = (tmp["Price"] - tmp["Price"].iloc[0]) * tmp["Quantity"]
                
                # --- Dividend Handling ---
                # Check for 'dividends' or 'Dividends' (standard yfinance)
                if 'dividends' in tmp.columns:
                    # Calculate Total Cash Payout = Per Share Dividend * Quantity
                    tmp["Dividends"] = tmp["dividends"].fillna(0) * qty
                elif 'Dividends' in tmp.columns:
                    tmp["Dividends"] = tmp["Dividends"].fillna(0) * qty
                else:
                    tmp["Dividends"] = 0.0

                tmp["Ticker"] = ticker
                tmp["Time"] = tmp.index
                
                # Select columns for final output
                # Added "Dividends" to the list
                pnl_time_data.append(
                    tmp[["Time", "Ticker", "Quantity", "Price", "Position Value ($)", "PnL", "Dividends"]]
                )
            except Exception as e:
                st.warning(f"{ticker}: Error building time series — {e}")

    return pd.concat(pnl_time_data, ignore_index=True) if pnl_time_data else pd.DataFrame()

# --- Metrics ---

def calculate_var(returns: pd.Series, confidence_level: float = CONFIDENCE_LEVEL) -> float:
    """
    Calculate the Value at Risk (VaR).
    
    Args:
        returns (pd.Series): Series of returns.
        confidence_level (float): The confidence level (default is global CONFIDENCE_LEVEL).
    """
    if returns.empty or returns.dropna().empty:
        return np.nan

    # Use the passed parameter 'confidence_level', not the global constant directly
    return np.percentile(returns.dropna(), (1 - confidence_level) * 100)


def calculate_cvar(returns: pd.Series, confidence_level: float = CONFIDENCE_LEVEL) -> float:
    """
    Calculate the Conditional Value at Risk (CVaR).
    
    Args:
        returns (pd.Series): Series of returns.
        confidence_level (float): The confidence level (default is global CONFIDENCE_LEVEL).
    """
    if returns.empty or returns.dropna().empty:
        return np.nan

    # PASS the confidence_level down to calculate_var so they stay in sync
    var = calculate_var(returns, confidence_level=confidence_level)
    
    cvar_values = returns[returns <= var]
    
    if cvar_values.empty:
        return np.nan
        
    return cvar_values.mean()

def daily_risk_free():
    """
    Helper function that returns the daily risk free return
    """
    return RISK_FREE_RATE / ANNUAL_TRADING_DAYS

def sharpe_ratio(returns: pd.Series) -> float:
    """
    Calculate the annualized Sharpe ratio.
    """
    if returns.empty or returns.dropna().empty:
        return np.nan

    excess = returns - daily_risk_free()
    std_excess = excess.std(ddof=0)

    # Guard against zero or near-zero volatility
    if std_excess < 1e-12:
        return np.nan

    return np.sqrt(ANNUAL_TRADING_DAYS) * excess.mean() / std_excess


def sortino_ratio(returns: pd.Series) -> float:
    """
    Calculate the annualized Sortino ratio.
    """
    if returns.empty or returns.dropna().empty:
        return np.nan

    excess = returns - daily_risk_free()
    downside = excess[excess < 0]  # use excess returns for downside risk
    downside_std = downside.std(ddof=0)

    # Guard against no downside risk (NaN or near-zero std)
    if pd.isna(downside_std) or downside_std < 1e-12:
        return np.nan

    return np.sqrt(ANNUAL_TRADING_DAYS) * excess.mean() / downside_std


def calmar_ratio(returns: pd.Series) -> float:
    """
    Calculate the Calmar ratio: annualized return divided by max drawdown.
    """
    if returns.empty or returns.dropna().empty:
        return np.nan
    cumulative = (1 + returns).cumprod()
    mdd = max_drawdown(cumulative)
    if len(returns) == 0:
        return np.nan
    annual_return = (1 + returns).prod() ** (ANNUAL_TRADING_DAYS / len(returns)) - 1
    return annual_return / abs(mdd) if mdd != 0 else np.nan

def max_drawdown(cumulative_returns: pd.Series) -> float:
    """
    Calculate the maximum drawdown from a cumulative returns series.

    Parameters
    ----------
    cumulative_returns : pd.Series
        Series of cumulative returns (e.g., equity curve).

    Returns
    -------
    float
        Maximum drawdown as a decimal (negative means loss).
    """
    rolling_max = cumulative_returns.cummax()
    drawdown = cumulative_returns / rolling_max - 1
    return drawdown.min()

def correlation_matrix(price_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the correlation matrix of asset returns.

    Parameters
    ----------
    price_df : pd.DataFrame
        DataFrame of asset prices with columns as tickers.

    Returns
    -------
    pd.DataFrame
        Correlation matrix of returns.
    """
    returns = price_df.pct_change(fill_method=None)
    return returns.corr()

def win_loss_stats(pnl_series: pd.Series) -> dict:
    wins = pnl_series[pnl_series > 0]
    losses = pnl_series[pnl_series < 0]

    win_rate = len(wins) / len(pnl_series) if len(pnl_series) > 0 else np.nan
    loss_rate = len(losses) / len(pnl_series) if len(pnl_series) > 0 else np.nan

    if losses.sum() == 0:
        if wins.sum() > 0:
            profit_factor = np.inf   # all wins, no losses
        else:
            profit_factor = np.nan   # no wins and no losses (all zeros)
    else:
        profit_factor = wins.sum() / abs(losses.sum())

    return {
        "win_rate": win_rate,
        "loss_rate": loss_rate,
        "profit_factor": profit_factor
    }

# Calculate equally weighted portfolio

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
    # Group by Ticker and select the first 'close' price (which corresponds to 
    # the oldest date fetched for the selected period).
    first_prices = portfolio_df.groupby('Ticker')['close'].first().reset_index(name='Starting_Price')
    
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

# Price forecast (Monte Carlo simulations)

def project_price_range(data):
    """
    Project the price range (min and max) 
    based on Monte Carlo simulations using the global CONFIDENCE_LEVEL.
    
    Parameters
    ----------
    data : pd.DataFrame
        DataFrame containing columns:
        ['Ticker', 'Close', 'Avg Return', 'Annualized Vol']
        
    Returns
    -------
    forecast_df : pd.DataFrame
        DataFrame with columns:
        ['Ticker', 'forecastLow', 'forecastHigh', 'periodMonths']
    """
    results = []
    
    # Convert period to years
    t = FORECAST_HORIZON / 12

    # Calculate percentiles based on global configuration
    # Example: If CONFIDENCE_LEVEL is 0.95 (95%):
    # lower_p = 5.0 (5th percentile)
    # upper_p = 95.0 (95th percentile)
    lower_p = (1 - CONFIDENCE_LEVEL) * 100
    upper_p = CONFIDENCE_LEVEL * 100

    for _, row in data.iterrows():
        # check if required columns exist to avoid key errors
        if 'close' not in row or 'avgReturn' not in row or 'annualizedVol' not in row:
            continue

        S0 = row['close']
        mu = row['avgReturn'] / 100  # Convert percentage to decimal
        sigma = row['annualizedVol'] / 100

        # Simulate end price using Geometric Brownian Motion
        Z = np.random.normal(0, 1, N_SIMS)
        ST = S0 * np.exp((mu - 0.5 * sigma**2) * t + sigma * np.sqrt(t) * Z)

        # Use dynamic percentiles
        forecast_min = np.percentile(ST, lower_p)
        forecast_max = np.percentile(ST, upper_p)

        results.append({
            'Ticker': row.get('Ticker', 'Unknown'), 
            'forecastLow': forecast_min,
            'forecastHigh': forecast_max,
            'periodMonths': FORECAST_HORIZON
        })

    return pd.DataFrame(results) if results else pd.DataFrame()

# Indicators

def ema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the Exponential Moving Average (EMA).
    """
    # Ensure sorting
    df = df.sort_values(['Ticker', 'Date'])

    # Group by Ticker and apply EMA
    ema_column_name = f'EMA_{EMA_PERIOD}'
    df[ema_column_name] = df.groupby('Ticker')['close'].transform(
        lambda x: x.ewm(span=EMA_PERIOD, adjust=False).mean()
    )
    return df

def distance_from_ema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the percentage distance between Close price and EMA(EMA_PERIOD).
    Formula: ((Close - EMA) / EMA) * 100
    """
    # Ensure sorting
    df = df.sort_values(['Ticker', 'Date'])

    # Calculate EMA locally
    ema_series = df.groupby('Ticker')['close'].transform(
        lambda x: x.ewm(span=EMA_PERIOD, adjust=False).mean()
    )
    
    col_name = f'dist_EMA_{EMA_PERIOD}'
    
    # Calculate percentage distance
    df[col_name] = ((df['close'] - ema_series) / ema_series) * 100
    
    return df


# --- New metrics logic ---
def calculate_beta(stock_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Helper function that calculates Beta given two aligned return series."""
    if stock_returns.empty or benchmark_returns.empty or len(stock_returns) < 2:
        return np.nan

    # Covariance matrix: [[Var(Stock), Cov(S,B)], [Cov(S,B), Var(Bench)]]
    cov_matrix = np.cov(stock_returns, benchmark_returns)
    covariance = cov_matrix[0, 1]
    benchmark_variance = cov_matrix[1, 1]
    
    return covariance / benchmark_variance if benchmark_variance != 0 else np.nan

def calculate_alpha(stock_returns: pd.Series, benchmark_returns: pd.Series, beta: float) -> float:
    """Helper function that calculates Annualized Alpha given returns and a pre-calculated Beta."""
    if pd.isna(beta) or stock_returns.empty:
        return np.nan
    
    rf_daily = daily_risk_free()
    
    # Calculate excess returns
    excess_stock = stock_returns.mean() - rf_daily
    excess_bench = benchmark_returns.mean() - rf_daily
    
    # Jensen's Alpha formula
    alpha_daily = excess_stock - (beta * excess_bench)
    
    return alpha_daily * ANNUAL_TRADING_DAYS

# Main metrics function
def calculate_annualized_metrics(df: pd.DataFrame, benchmark_rets: pd.Series = None) -> pd.DataFrame:
    """
    Calculates annualized metrics (Return, Vol, Sharpe) and Risk metrics (Beta, Alpha).
    
    Args:
        df (pd.DataFrame): Data containing 'Ticker', 'Date', 'dailyReturn'.
        benchmark_rets (pd.Series, optional): Series of benchmark daily returns with DatetimeIndex. 
                                              If None, attempts to extract BENCHMARK_INDEX from df.
    """
    
    # 1. Attempt to resolve Benchmark Returns if not provided
    if benchmark_rets is None:
        if 'Ticker' in df.columns and BENCHMARK_INDEX in df['Ticker'].values:
            # Extract benchmark, ensure Date index for alignment
            bench_df = df[df['Ticker'] == BENCHMARK_INDEX].copy()
            # Ensure we have a proper datetime index or column to set as index
            if 'Date' in bench_df.columns:
                bench_df = bench_df.set_index('Date')
            benchmark_rets = bench_df['dailyReturn']

    # 2. Define the aggregation logic
    def aggregate_metrics(group):
        # Drop NaNs to ensure clean calculation
        clean_group = group.dropna(subset=['dailyReturn'])
        returns = clean_group['dailyReturn']
        N = len(returns)
        
        # Initialize default NaN results
        metrics = {
            'avgReturn': np.nan, 
            'annualizedVol': np.nan, 
            'sharpeRatio': np.nan,
            'beta': np.nan,
            'alpha': np.nan
        }

        if N < 5: 
            return pd.Series(metrics)

        # --- A. Standard Metrics ---
        daily_vol = returns.std()
        annualized_vol = daily_vol * np.sqrt(ANNUAL_TRADING_DAYS)
        
        total_return = (1 + returns).prod() - 1 
        annualization_factor = ANNUAL_TRADING_DAYS / N 
        annualized_return = (1 + total_return) ** annualization_factor - 1
        
        sharpe = (annualized_return - RISK_FREE_RATE) / annualized_vol if annualized_vol != 0 else np.nan

        metrics['avgReturn'] = annualized_return * 100
        metrics['annualizedVol'] = annualized_vol * 100
        metrics['sharpeRatio'] = sharpe

        # --- B. Risk Metrics (Beta/Alpha) ---
        # We need the benchmark returns to exist and overlap with this stock's dates
        if benchmark_rets is not None and not benchmark_rets.empty:
            # Align stock returns with benchmark returns on Date
            # Assume group has 'Date' column; set it as index for alignment
            stock_series = clean_group.set_index('Date')['dailyReturn']
            
            # Intersection of dates
            aligned_df = pd.concat([stock_series, benchmark_rets], axis=1, join='inner').dropna()
            
            if len(aligned_df) > 10: # Minimum overlapping days required for valid Beta
                stock_aligned = aligned_df.iloc[:, 0]
                bench_aligned = aligned_df.iloc[:, 1]
                
                beta_val = calculate_beta(stock_aligned, bench_aligned)
                alpha_val = calculate_alpha(stock_aligned, bench_aligned, beta_val)
                
                metrics['beta'] = beta_val
                metrics['alpha'] = alpha_val * 100

        return pd.Series(metrics)

    # 3. Ensure dailyReturn exists
    if 'dailyReturn' not in df.columns:
        df['dailyReturn'] = df.groupby('Ticker')['close'].pct_change()

    # 4. Apply aggregation
    # include_groups=False is required for pandas >= 2.2.0 compatibility
    annual_metrics_df = df.groupby('Ticker').apply(aggregate_metrics, include_groups=False).reset_index()

    # 5. Merge with latest dates (to keep metadata valid)
    latest_dates = df.groupby('Ticker').tail(1)[['Ticker', 'Date']].reset_index(drop=True)
    final_metrics_df = pd.merge(latest_dates, annual_metrics_df, on='Ticker')
    
    return final_metrics_df