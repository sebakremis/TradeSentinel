# src/run_pnl.py
import argparse
import pandas as pd
from ensure_data import ensure_prices, as_close_panel
from pnl_calculator import calculate_pnl
from log_utils import info, warn, error, set_verbose

def main():
    parser = argparse.ArgumentParser(description="Run PnL calculation for given tickers.")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable detailed logging output"
    )
    args = parser.parse_args()

    # Set global verbosity
    set_verbose(args.verbose)

    tickers = ["AAPL", "MSFT", "FAKE"]
    positions = pd.DataFrame({
        "Ticker": ["AAPL", "MSFT", "FAKE"],
        "Quantity": [50, 30, 10],
        "EntryPrice": [150.0, 280.0, 100.0]
    })

    price_map = ensure_prices(tickers, interval="1m", lookback_days=5)

    valid_tickers = []
    for ticker, df in price_map.items():
        if df.empty:
            error(f"No data available for {ticker} — skipping this ticker.")
            continue

        freq = pd.infer_freq(df.index)
        if freq is None and len(df) > 1:
            avg_delta = (df.index[1] - df.index[0]).total_seconds()
            if avg_delta <= 60:
                freq = "1min"
            elif avg_delta >= 86400:
                freq = "1d"
            else:
                freq = "unknown"

        info(f"{ticker} data frequency: {freq} ({'daily fallback' if freq == '1d' else 'intraday'})")
        valid_tickers.append(ticker)

    positions = positions[positions["Ticker"].isin(valid_tickers)]
    if positions.empty:
        error("No valid tickers left to calculate PnL.")
        return

    closes = as_close_panel({t: price_map[t] for t in valid_tickers})

    try:
        pnl_df = calculate_pnl(positions, closes)
        if args.verbose:
            print("\nPnL Results:")
            print(pnl_df)
        else:
            print("\nPnL Summary:")
            for _, row in pnl_df.iterrows():
                print(f"{row['Ticker']}: PnL = {row['PnL']:.2f}")
        print(f"\nTotal PnL: {pnl_df['PnL'].sum():.2f}")
    except ValueError as e:
        error(str(e))

if __name__ == "__main__":
    main()
