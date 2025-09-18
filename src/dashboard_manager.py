# src/dashboard_manager.py
from data_fetch import get_market_data
from storage import save_prices

# Active mapping used by main.py for dashboard data
intervals_main = {
    "3mo": "30m",
    "1y": "1d"
}

# Full interval mapping
intervals_full = {
    "1d":  ["1m", "5m", "15m", "30m", "1h"],
    "5d":  ["5m", "15m", "30m", "1h", "1d"],
    "1mo": ["15m", "30m", "1h", "1d", "1wk"],
    "3mo": ["15m", "30m", "1h", "1d", "1wk"],
    "6mo": ["1d", "1wk", "1mo"],
    "1y":  ["1d", "1wk", "1mo"],
    "ytd": ["1d", "1wk", "1mo"],
    "max": ["1d", "1wk", "1mo"]
}

def process_dashboard_data(ticker: str):
    for period, interval in intervals_main.items():
        print(f"Fetching {period} data at {interval} interval for {ticker}")
        data = get_market_data(ticker, period, interval)
        save_prices(ticker, period, interval, data)
