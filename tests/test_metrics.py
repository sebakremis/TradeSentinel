import pandas as pd
from src.metrics import max_drawdown

def test_max_drawdown_simple_case():
    # Simulate a portfolio value series
    values = pd.Series([100, 120, 80, 90, 150, 140])
    # Cumulative returns = values / values[0]
    cum_returns = values / values.iloc[0]

    # Expected max drawdown:
    # Peak at 120, trough at 80 → drawdown = (80 - 120) / 120 = -0.3333...
    expected = -1 * (120 - 80) / 120  # 0.3333...

    result = max_drawdown(cum_returns)

    assert abs(result - expected) < 1e-6
