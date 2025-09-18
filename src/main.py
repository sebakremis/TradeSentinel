# src/main.py

import argparse
import tickers_store
from data_fetch import get_market_data
from storage import save_prices_incremental
from dashboard_manager import process_dashboard_data


def main():
    tickers = tickers_store.load_followed_tickers()
    
    parser = argparse.ArgumentParser(
        description="TS-PortfolioAnalytics: Fetch and store market data for dashboard or custom intervals."
    )
    parser.add_argument(
        "--mode",
        choices=["dashboard", "custom"],
        default="dashboard",
        help="Choose 'dashboard' mode (fixed intervals from dashboard_manager) "
             "or 'custom' mode (CLI-provided period/interval)."
    )
    parser.add_argument(
        "--period",
        help="Custom period (e.g., 3mo, 1y, 5d). Required if mode=custom."
    )
    parser.add_argument(
        "--interval",
        help="Custom interval (e.g., 30m, 1d, 1wk). Required if mode=custom."
    )
    args = parser.parse_args()

    if args.mode == "dashboard":
        # Use the fixed mapping from dashboard_manager
        for ticker in tickers:
            process_dashboard_data(ticker)

    else:  # custom mode
        if not args.period or not args.interval:
            raise ValueError("Custom mode requires both --period and --interval arguments.")
        for ticker in tickers:
            print(f"Fetching {args.period} data at {args.interval} interval for {ticker}")
            data = get_market_data(ticker, args.period, args.interval)
            save_prices_incremental(ticker, args.period, args.interval, data)


if __name__ == "__main__":
    main()




