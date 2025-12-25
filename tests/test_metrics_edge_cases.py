import pytest
import numpy as np
import pandas as pd
from src.analytics import (
    sharpe_ratio,
    sortino_ratio,
    calmar_ratio,
    calculate_var,
    calculate_cvar,
    win_loss_stats,
)

# -------------------------
# Sharpe Ratio Edge Cases
# -------------------------

def test_sharpe_ratio_empty_series():
    returns = pd.Series([], dtype=float)
    result = sharpe_ratio(returns, risk_free_rate=0.0)
    assert np.isnan(result)

def test_sharpe_ratio_constant_returns():
    returns = pd.Series([0.01] * 10)
    result = sharpe_ratio(returns, risk_free_rate=0.0)
    assert np.isnan(result) or result == 0.0

# -------------------------
# Sortino Ratio Edge Cases
# -------------------------

def test_sortino_ratio_all_negative():
    returns = pd.Series([-0.01, -0.02, -0.03])
    result = sortino_ratio(returns, risk_free_rate=0.0)
    assert result < 0

def test_sortino_ratio_no_negative_returns():
    returns = pd.Series([0.01, 0.02, 0.03])
    result = sortino_ratio(returns, risk_free_rate=0.0)
    assert np.isnan(result)  # no downside risk → undefined


# -------------------------
# Calmar Ratio Edge Cases
# -------------------------

def test_calmar_ratio_empty_series():
    returns = pd.Series([], dtype=float)
    result = calmar_ratio(returns)
    assert np.isnan(result)

def test_calmar_ratio_all_negative():
    returns = pd.Series([-0.01, -0.02, -0.03])
    result = calmar_ratio(returns)
    assert result < 0

# -------------------------
# VaR & CVaR Edge Cases
# -------------------------

def test_var_with_outlier():
    returns = pd.Series([0.01, 0.02, -0.5, 0.03, 0.04])
    var_95 = calculate_var(returns, confidence_level=0.95)
    assert var_95 <= -0.3


def test_cvar_different_confidence_levels():
    returns = pd.Series(np.random.normal(0, 0.01, 1000))
    cvar_90 = calculate_cvar(returns, confidence_level=0.90)
    cvar_99 = calculate_cvar(returns, confidence_level=0.99)
    assert cvar_99 <= cvar_90

# -------------------------
# Win/Loss Stats Edge Cases
# -------------------------

def test_win_loss_stats_all_wins():
    returns = pd.Series([0.01, 0.02, 0.03])
    stats = win_loss_stats(returns)
    assert stats["win_rate"] == 1.0
    assert stats["loss_rate"] == 0.0
    assert np.isinf(stats["profit_factor"])

def test_win_loss_stats_all_losses():
    returns = pd.Series([-0.01, -0.02, -0.03])
    stats = win_loss_stats(returns)
    assert stats["win_rate"] == 0.0
    assert stats["loss_rate"] == 1.0
    assert stats["profit_factor"] == 0.0

def test_win_loss_stats_with_zeros():
    returns = pd.Series([0.0, 0.01, -0.01])
    stats = win_loss_stats(returns)
    assert np.isclose(stats["win_rate"] + stats["loss_rate"], 2/3)
