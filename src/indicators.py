import pandas as pd
from src.etl import load_update_log
from src.config import stocks_folder

def breakout(min_lookback: int = 10)-> list:
    """
    Identify tickers that have broken out to new highs in the last `min_lookback` days.
    """
    tickers_log = load_update_log()
    breakout_tickers = []

    for ticker, ticker_info in tickers_log.items():
        last_date = ticker_info["last_date"]
        last_price = ticker_info["last_price"]
        prices_file = stocks_folder/f"prices/{ticker}.parquet"
        prices_df = pd.read_parquet(prices_file)
        lookback_df = prices_df[prices_df.index < last_date].tail(min_lookback)
        if not lookback_df.empty and last_price > lookback_df['high'].max():
            breakout_tickers.append(ticker)

    breakout_tickers.sort()
    return breakout_tickers

if __name__ == "__main__":
    result = breakout()
    print("Breakout Tickers:", result)