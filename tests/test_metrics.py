import pandas as pd
import numpy as np
import pytest

from src.analytics import (
    max_drawdown,
    calculate_var,
    calculate_cvar,
    sharpe_ratio,
    sortino_ratio,
    calmar_ratio,
    win_loss_stats
)

def test_max_drawdown_simple_case():
    values = pd.Series([100, 120, 80, 90, 150, 140])
    cum_returns = values / values.iloc[0]
    expected = -1 * (120 - 80) / 120
    result = max_drawdown(cum_returns)
    assert abs(result - expected) < 1e-6

def test_calculate_var_known_values():
    returns = pd.Series([0.01, -0.02, 0.015, -0.005, 0.03])
    var_95 = calculate_var(returns, confidence_level=0.95)
    # For a small dataset, we can check the quantile directly
    expected = returns.quantile(0.05)
    assert np.isclose(var_95, expected)

def test_calculate_cvar_known_values():
    returns = pd.Series([0.01, -0.02, 0.015, -0.005, 0.03])
    cvar_95 = calculate_cvar(returns, confidence_level=0.95)
    # CVaR should be the mean of returns below the VaR threshold
    var_95 = returns.quantile(0.05)
    expected = returns[returns <= var_95].mean()
    assert np.isclose(cvar_95, expected)

def test_sharpe_ratio_positive():
    returns = pd.Series([0.01, 0.02, 0.015, 0.005, 0.03])
    result = sharpe_ratio(returns, risk_free_rate=0.0)
    assert result > 0

def test_sortino_ratio_positive():
    returns = pd.Series([0.01, -0.02, 0.015, -0.005, 0.03, -0.01])
    result = sortino_ratio(returns, risk_free_rate=0.0)
    assert not np.isnan(result)
    assert result > 0


def test_calmar_ratio_positive():
    returns = pd.Series([0.01, 0.02, 0.015, -0.005, 0.03])
    result = calmar_ratio(returns)
    assert result > 0

def test_win_loss_stats_counts():
    returns = pd.Series([0.01, -0.02, 0.015, -0.005, 0.03])
    stats = win_loss_stats(returns)

    # win_rate should be wins / total trades
    assert np.isclose(stats["win_rate"], 3/5)
    assert np.isclose(stats["loss_rate"], 2/5)

    # profit_factor should be sum of profits / sum of losses (absolute value)
    profits = returns[returns > 0].sum()
    losses = abs(returns[returns < 0].sum())
    expected_pf = profits / losses
    assert np.isclose(stats["profit_factor"], expected_pf)


