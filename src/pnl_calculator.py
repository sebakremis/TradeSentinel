# src/pnl_calculator.py
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

