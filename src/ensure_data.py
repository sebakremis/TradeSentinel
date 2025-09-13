# src/ensure_data.py
import yfinance as yf
from log_utils import info, warn, error

def ensure_prices(tickers, period="5d", interval="1d"):
    """
    Fetch historical price data for each ticker and ensure a 'Close' column exists.
    Returns:
        dict[str, pd.DataFrame]: Mapping of ticker -> DataFrame with at least a 'Close' column.
    """
    prices = {}
    for ticker in tickers:
        try:
            info(f"Fetching data for {ticker}...")
            df = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True  # ✅ Explicit to avoid FutureWarning
            )

            if df.empty:
                warn(f"No data returned for {ticker}, skipping.")
                continue

            # Ensure 'Close' column exists
            if "Close" not in df.columns:
                if "Adj Close" in df.columns:
                    warn(f"'Close' missing for {ticker}, using 'Adj Close' instead.")
                    df["Close"] = df["Adj Close"]
                else:
                    error(f"No 'Close' or 'Adj Close' column for {ticker}, skipping.")
                    continue

            prices[ticker] = df

        except Exception as e:
            error(f"Error fetching data for {ticker}: {e}")

    return prices

