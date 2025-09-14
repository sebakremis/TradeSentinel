# src/pnl_calculator.py
"""
pnl_calculator.py
=================

Utility for calculating and displaying Profit & Loss (PnL) metrics for one or
more stock tickers based on historical closing price data.

This module provides a single function, `calculate_pnl`, which:
1. Iterates over a list of tickers.
2. Retrieves their corresponding price DataFrames from a provided dictionary.
3. Calculates absolute and percentage PnL between the first and last available
   closing prices.
4. Logs warnings for missing or empty data, and errors for missing columns or
   calculation issues.
5. Prints per‑ticker PnL results and an overall portfolio summary, regardless
   of verbosity settings.

Features
--------
- **Per‑Ticker PnL**:
  - Absolute change in price.
  - Percentage change relative to the starting price.

- **Portfolio Summary**:
  - Aggregated total PnL across all tickers.
  - Overall percentage change relative to the combined starting value.

- **Robust Error Handling**:
  - Skips tickers with no data or missing 'Close' column.
  - Catches and logs unexpected exceptions without halting execution.

Functions
---------
- `calculate_pnl(tickers: list[str], close_prices_dict: dict[str, pandas.DataFrame]) -> None`  
  Compute and print PnL for each ticker and the overall portfolio.

Parameters
----------
tickers : list[str]
    List of ticker symbols to process.
close_prices_dict : dict[str, pandas.DataFrame]
    Mapping of ticker symbols to DataFrames containing at least a 'Close' column.

Dependencies
------------
- pandas (for DataFrame operations)
- log_utils (for logging warnings and errors)

Usage Example
-------------
    from pnl_calculator import calculate_pnl

    tickers = ["AAPL", "MSFT"]
    prices = {
        "AAPL": aapl_df,  # DataFrame with 'Close' column
        "MSFT": msft_df
    }

    calculate_pnl(tickers, prices)

Notes
-----
- The DataFrame for each ticker must contain a 'Close' column with numeric values.
- Results are printed directly to stdout; there is no return value.
"""

from log_utils import info, warn, error

def calculate_pnl(tickers, close_prices_dict):
    """
    Calculate and log PnL for each ticker from a dict of DataFrames.
    Always prints per-ticker and portfolio results, even without verbose mode.
    """
    total_pnl = 0.0
    total_start_value = 0.0
    results_found = False

    for ticker in tickers:
        df = close_prices_dict.get(ticker)

        if df is None or df.empty:
            warn(f"No price data for {ticker}, skipping.")
            continue

        try:
            start_price = df["Close"].iloc[0].item()
            end_price   = df["Close"].iloc[-1].item()

            pnl = end_price - start_price
            pct_change = (pnl / start_price) * 100

            total_pnl += pnl
            total_start_value += start_price
            results_found = True

            # ✅ Always print results, bypassing verbosity
            print(f"{ticker} PnL: {pnl:.2f} ({pct_change:.2f}%)")

        except KeyError:
            error(f"Missing 'Close' column for {ticker}, skipping.")
        except Exception as e:
            error(f"Error calculating PnL for {ticker}: {e}")

    # ✅ Always print portfolio summary
    if results_found and total_start_value > 0:
        total_pct_change = (total_pnl / total_start_value) * 100
        print(f"Portfolio Total PnL: {total_pnl:.2f} ({total_pct_change:.2f}%)")
    elif not results_found:
        print("No PnL results to display.")

