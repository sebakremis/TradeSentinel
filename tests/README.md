# 🧪 TradeSentinel Test Suite

This directory contains the automated tests for the **portfolio metrics** implemented in [`src/metrics.py`](../src/metrics.py).  
The tests are designed to validate both **core functionality** and **robust handling of edge cases**.

---

## 📂 Test Files

- **`test_metrics.py`**  
  Covers the main correctness of each metric function with straightforward inputs.

- **`test_metrics_edge_cases.py`**  
  Extends coverage to unusual or extreme scenarios, ensuring resilience in real‑world usage.

---

## ✅ Metrics Tested

The following functions from `metrics.py` are under test:

- `sharpe_ratio`  
- `sortino_ratio`  
- `calmar_ratio`  
- `calculate_var`  
- `calculate_cvar`  
- `win_loss_stats`  
- `max_drawdown`

---

## 🔍 What We Test

### Core Tests (`test_metrics.py`)
- Correctness of calculations on small, known datasets
- Expected outputs for positive/negative return series
- Sanity checks (e.g. Sharpe > 0 when returns are consistently positive)

### Edge Case Tests (`test_metrics_edge_cases.py`)
- **Empty or constant series** → functions return `NaN` instead of crashing  
- **All wins / all losses / all zeros** → `win_loss_stats` handles division by zero gracefully (`∞`, `0.0`, or `NaN`)  
- **No downside risk** → `sortino_ratio` returns `NaN` or `∞` depending on convention  
- **Extreme outliers** → VaR and CVaR reflect tail risk appropriately  
- **Different confidence levels** → CVaR scales correctly at 90%, 95%, 99%  
- **Annualization effects** → Sharpe and Sortino ratios behave differently for daily vs monthly data

---

## ▶️ Running Tests Locally

Install dependencies and run the suite:

```bash
pip install -r requirements.txt
pytest
```

## ✅ Test Results

All tests are currently passing:

![All tests passing](docs/images/tests_passed.png)




