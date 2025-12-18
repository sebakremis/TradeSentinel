# src/etl.py
import pandas as pd
import yfinance as yf
from .config import DATA_DIR, stocks_folder, tickers_file, metadata_file
from .tickers_manager import load_followed_tickers

# Define the path to the followed tickers CSV file
filepath = tickers_file
filename = filepath.name
   
def fetch_prices(ticker: str, period: str = None, start: str = None, interval: str = '1d') -> pd.DataFrame:
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
        
        # Format column names
        data.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Dividends': 'dividends',
            'Stock Splits': 'stockSplits'
        }, inplace=True)

        return data
    except Exception as e:
        print(f"Error fetching data for ticker {ticker}: {e}")
        return pd.DataFrame()

def fetch_metadata(ticker: str) -> dict:
    """
    Extract metadata for a given ticker using yfinance.
    Returns a dictionary with relevant metadata fields.
    """
    metadata = {}
    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info
        metadata = {
            'Ticker': ticker,
            'shortName': info.get('shortName', ''),
            'sector': info.get('sector', ''),
            'industry': info.get('industry', ''),
            'country': info.get('country', ''),
            'marketCap': info.get('marketCap', 0),
            'beta': info.get('beta', None),
            'dividendYield': info.get('dividendYield', None),
            '52WeekHigh': info.get('fiftyTwoWeekHigh', None),
            '52WeekLow': info.get('fiftyTwoWeekLow', None),
            # valuation data
            'trailingPE': info.get('trailingPE', None),
            'forwardPE': info.get('forwardPE', None),
            'priceToBook': info.get('priceToBook', None),
            'priceToSalesTrailing12Months': info.get('priceToSalesTrailing12Months', None),
            'enterpriseToEbitda': info.get('enterpriseToEbitda', None),
            # profitability data
            'returnOnAssets': info.get('returnOnAssets', None),
            'returnOnEquity': info.get('returnOnEquity', None),
            'profitMargins': info.get('profitMargins', None),
            # last updated
            'lastUpdated': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        print(f"Metadata for {ticker} extracted successfully.")
        return metadata
    except Exception as e:
        print(f"Error extracting metadata for ticker {ticker}: {e}")
        return {}


def update_stock_prices(tickers_df: pd.DataFrame):
    """
    Updates the stock prices database with the latest information for all followed tickers.
    Creates the parket file for the ticker if it does not exist.
    """   
    
    for _, row in tickers_df.iterrows():
        ticker = row['Ticker']
        stock_prices_file = stocks_folder/f"prices/{ticker}.parquet"
        
        # --- Fetch price data and update parquet file ---
        if stock_prices_file.exists():
            existing_data = pd.read_parquet(stock_prices_file)
            existing_data.index = pd.to_datetime(existing_data.index)
            if not existing_data.empty:
                # Determine the last date in existing data
                last_date = existing_data.index.max().date()
                new_start_date = pd.Timestamp(last_date) + pd.Timedelta(days=1)
                # Check if new_start_date is in the future
                if new_start_date >= pd.Timestamp.today().normalize():
                    print(f"No new data for {ticker}.")
                    continue            
                new_data = fetch_prices(ticker, start=new_start_date.strftime('%Y-%m-%d'))
                if not new_data.empty:
                    updated_data = pd.concat([existing_data, new_data])
                    updated_data = updated_data[~updated_data.index.duplicated(keep='last')]
                    updated_data.to_parquet(stock_prices_file)
                    print(f"Updated data for {ticker} saved to {stock_prices_file}")
            else:
                # If existing data is empty, fetch all available data
                updated_data = fetch_prices(ticker, period='5y')
                updated_data.to_parquet(stock_prices_file)
                print(f"Updated data for {ticker} saved to {stock_prices_file}")        

        else:
            # If file does not exist, fetch all available data
            updated_data = fetch_prices(ticker, period='5y')
            updated_data.to_parquet(stock_prices_file)
            print(f"Updated data for {ticker} saved to {stock_prices_file}")

def update_stock_metadata(tickers_df: pd.DataFrame):
    """
    Updates the stock metadata database with the latest information for all followed tickers.
    """
    metadata_list = []

    for _, row in tickers_df.iterrows():
        ticker = row['Ticker']
       
        # if metadata file exists, check if ticker is already present
        if metadata_file.exists():
            existing_metadata = pd.read_csv(metadata_file)
            if ticker in existing_metadata['Ticker'].values:
                # check last updated date
                existing_ticker_metadata = existing_metadata[existing_metadata['Ticker'] == ticker].iloc[0]
                last_updated_str = existing_ticker_metadata.get('lastUpdated', '')
                if last_updated_str:
                    last_updated = pd.to_datetime(last_updated_str)
                    if (pd.Timestamp.now() - last_updated).days < 7:
                        print(f"Metadata for {ticker} is up to date.")
                        continue
        ticker_metadata = fetch_metadata(ticker)
        metadata_list.append(ticker_metadata)

    # Save metadata to CSV
    if metadata_list:
        metadata_df = pd.DataFrame(metadata_list)
        if metadata_file.exists():
            existing_metadata = pd.read_csv(metadata_file)
            combined_metadata = pd.concat([existing_metadata, metadata_df])
            combined_metadata = combined_metadata.drop_duplicates(subset=['ticker'], keep='last')
            combined_metadata.to_csv(metadata_file, index=False)
        else:
            metadata_df.to_csv(metadata_file, index=False)
        print(f"Metadata updated and saved to {metadata_file}")


def update_stock_database():    
    """
    Updates both stock prices and metadata databases.
    """
    tickers_df = load_followed_tickers()   
    stocks_folder.mkdir(parents=True, exist_ok=True)
    update_stock_prices(tickers_df)
    update_stock_metadata(tickers_df)



if __name__ == "__main__":
    """
    Main execution to update stock database.
    """
    update_stock_database()    
  