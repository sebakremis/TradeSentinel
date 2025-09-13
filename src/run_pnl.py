# src/run_pnl.py
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


