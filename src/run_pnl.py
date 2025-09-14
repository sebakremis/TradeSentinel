# src/run_pnl.py
"""
run_pnl.py
==========

Command-line utility for running Profit & Loss (PnL) calculations on one or more
stock tickers using historical market data from Yahoo Finance.

This script:
1. Parses command-line arguments for tickers, data period, interval, and verbosity.
2. Validates user-supplied period and interval against allowed Yahoo Finance values.
3. Fetches historical closing prices via `ensure_prices`.
4. Calculates and displays PnL results using `calculate_pnl`.
5. Logs progress, warnings, and errors with optional verbose output.

Features
--------
- **Ticker Selection**:
  - Specify tickers via `--tickers` (space-separated).
  - Defaults to: AAPL, MSFT, TSLA.

- **Data Parameters**:
  - `--period`: Historical data period (default: 5d).
  - `--interval`: Data interval (default: 1d).
  - Both validated against predefined allowed values.

- **Verbose Logging**:
  - `--verbose` flag enables INFO-level logging.

- **Error Handling**:
  - Catches and logs exceptions without crashing.

Functions
---------
- `validate_choice(value: str, valid_list: list[str], arg_name: str) -> str`  
  Validate that a CLI argument value is in the allowed list; raise `ArgumentTypeError` if not.

- `main() -> None`  
  Parse arguments, run data retrieval, and execute PnL calculation.

Dependencies
------------
- argparse (standard library)
- ensure_data.ensure_prices
- pnl_calculator.calculate_pnl
- log_utils (for logging)
- yfinance (indirectly, via ensure_data)
- pandas (indirectly, via ensure_data and pnl_calculator)

Usage Example
-------------
    python src/run_pnl.py --tickers AAPL MSFT TSLA --period 1mo --interval 1d --verbose

Example Output
--------------
    [2025-09-14 17:05:02] INFO: Running PnL for: AAPL, MSFT, TSLA
    ...PnL results table...

Notes
-----
- This script is intended for terminal use; for an interactive UI, use `dashboard.py`.
- Yahoo Finance rate limits may apply when fetching data.
"""

import argparse
from ensure_data import ensure_prices
from pnl_calculator import calculate_pnl
from log_utils import set_verbose, info, error

DEFAULT_TICKERS = ["AAPL", "MSFT", "TSLA"]

# Allowed Yahoo Finance values
VALID_PERIODS = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
VALID_INTERVALS = ["1m", "2m", "5m", "15m", "30m", "60m", "90m",
                   "1h", "1d", "5d", "1wk", "1mo", "3mo"]

def validate_choice(value, valid_list, arg_name):
    """Raise argparse error if value not in valid_list."""
    if value not in valid_list:
        raise argparse.ArgumentTypeError(
            f"Invalid {arg_name}: '{value}'. "
            f"Allowed values are: {', '.join(valid_list)}"
        )
    return value

def main():
    parser = argparse.ArgumentParser(description="Run PnL calculations for given tickers")
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="List of tickers to process (e.g., AAPL MSFT TSLA)"
    )
    parser.add_argument(
        "--period",
        type=lambda v: validate_choice(v, VALID_PERIODS, "period"),
        default="5d",
        help=f"Data period to fetch. Allowed: {', '.join(VALID_PERIODS)}. Default: 5d"
    )
    parser.add_argument(
        "--interval",
        type=lambda v: validate_choice(v, VALID_INTERVALS, "interval"),
        default="1d",
        help=f"Data interval. Allowed: {', '.join(VALID_INTERVALS)}. Default: 1d"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    args = parser.parse_args()

    set_verbose(args.verbose)
    tickers = args.tickers if args.tickers else DEFAULT_TICKERS
    info(f"Running PnL for: {', '.join(tickers)}")

    try:
        close_prices = ensure_prices(tickers, period=args.period, interval=args.interval)
        calculate_pnl(tickers, close_prices)
    except Exception as e:
        error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()


