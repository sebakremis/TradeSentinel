# src/etl.py
import pandas as pd
import yfinance as yf
from config import DATA_DIR

def load_tickers_from_csv(filepath: str) -> pd.DataFrame:
    """
    Load tickers from a CSV file.
    Expects a CSV with at least a 'Ticker' column.
    """
    try:
        tickers_df = pd.read_csv(filepath)
        if 'Ticker' not in tickers_df.columns:
            raise ValueError("CSV file must contain a 'Ticker' column.")
        return tickers_df
    except Exception as e:
        print(f"Error loading tickers from {filepath}: {e}")
        return pd.DataFrame(columns=['Ticker'])
    
def fetch_ticker_data(ticker: str, period: str = None, start: str = None, interval: str = '1d') -> pd.DataFrame:
    """
    Fetch historical data for a given ticker using yfinance.
    It accepts either a period or a start date.
    """
    data = pd.DataFrame()
    try:
        yf_ticker = yf.Ticker(ticker) # Initialize yfinance Ticker object
        if period:
            data = yf_ticker.history(period=period, interval=interval)
        elif start:
            data = yf_ticker.history(start=start, interval=interval)
        else:
            raise ValueError("Either 'period' or 'start' must be provided.")
        return data
    except Exception as e:
        print(f"Error fetching data for ticker {ticker}: {e}")
        return pd.DataFrame()

def update_stock_database():
    """
    Updates the stock data database with the latest information for all followed tickers.
    Creates the parket file for the ticker if it does not exist.
    """
    tickers_file = DATA_DIR / 'tickers_list.csv'
    tickers_df = load_tickers_from_csv(tickers_file)

    stocks_folder = DATA_DIR / 'stocks'
    
    for _, row in tickers_df.iterrows():
        ticker = row['Ticker']
        stock_file = stocks_folder / f"{ticker}.parquet"
        
        # Fetch historical data
        if stock_file.exists():
            existing_data = pd.read_parquet(stock_file)
            last_date = existing_data.index.max().date()
            new_data = fetch_ticker_data(ticker, start=str(last_date + pd.Timedelta(days=1)))
            updated_data = pd.concat([existing_data, new_data]).drop_duplicates()
        else:
            updated_data = fetch_ticker_data(ticker, period='5y')
        
        # Save updated data
        updated_data.to_parquet(stock_file)
        print(f"Updated data for {ticker} saved to {stock_file}")
    
if __name__ == "__main__":
    update_stock_database()    
  