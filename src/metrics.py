# src/metrics.py
"""
metrics.py — Advanced portfolio and trading performance metrics for TradeSentinel.

This module provides reusable functions to calculate advanced risk, return, and
performance statistics for portfolios or individual assets. It is designed to be
imported into the Streamlit dashboard (`dashboard.py`) or used in offline analysis scripts.

Functions included:
- Value at Risk (VaR) and Conditional VaR (CVaR / Expected Shortfall)
- Sharpe, Sortino, and Calmar ratios
- Maximum drawdown
- Correlation matrix
- Win rate, loss rate, and profit factor

Robustness & Safety
-------------------
- All functions are pure and side-effect free: they take pandas Series/DataFrames as input
  and return numeric results or DataFrames, making them easy to test and reuse.
- Empty or all-NaN inputs are handled gracefully, returning `np.nan` rather than raising errors.
- Division-by-zero cases (e.g., zero standard deviation or zero max drawdown) are explicitly guarded.
- Behaviour on insufficient data is predictable and safe for use in automated pipelines.

Typical usage:
    from metrics import sharpe_ratio, max_drawdown
    sr = sharpe_ratio(daily_returns)
    mdd = max_drawdown((1 + daily_returns).cumprod())
"""

import numpy as np
import pandas as pd


def calculate_var(returns: pd.Series, confidence_level: float = 0.95) -> float:
    """
    Calculate the Value at Risk (VaR) at the given confidence level.
    """
    if returns.empty or returns.dropna().empty:
        return np.nan
    return np.percentile(returns.dropna(), (1 - confidence_level) * 100)


def calculate_cvar(returns: pd.Series, confidence_level: float = 0.95) -> float:
    """
    Calculate the Conditional Value at Risk (CVaR) at the given confidence level.
    """
    if returns.empty or returns.dropna().empty:
        return np.nan
    var = calculate_var(returns, confidence_level)
    cvar_values = returns[returns <= var]
    if cvar_values.empty:
        return np.nan
    return cvar_values.mean()


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Calculate the annualized Sharpe ratio."""
    if returns.empty or returns.dropna().empty:
        return np.nan

    excess = returns - (risk_free_rate / 252)
    std_excess = excess.std(ddof=0)

    # Guard against zero or near-zero volatility
    if std_excess < 1e-12:
        return np.nan

    return np.sqrt(252) * excess.mean() / std_excess


def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Calculate the annualized Sortino ratio."""
    if returns.empty or returns.dropna().empty:
        return np.nan

    excess = returns - (risk_free_rate / 252)
    downside = excess[excess < 0]  # use excess returns for downside risk
    downside_std = downside.std(ddof=0)

    # Guard against no downside risk (NaN or near-zero std)
    if pd.isna(downside_std) or downside_std < 1e-12:
        return np.nan

    return np.sqrt(252) * excess.mean() / downside_std


def calmar_ratio(returns: pd.Series) -> float:
    """Calculate the Calmar ratio: annualized return divided by max drawdown."""
    if returns.empty or returns.dropna().empty:
        return np.nan
    cumulative = (1 + returns).cumprod()
    mdd = max_drawdown(cumulative)
    if len(returns) == 0:
        return np.nan
    annual_return = (1 + returns).prod() ** (252 / len(returns)) - 1
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

