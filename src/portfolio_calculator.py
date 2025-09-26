# src/portfolio_calculator.py
import pandas as pd
from typing import Dict, Any, List, Tuple
import numpy as np

# Note: This file relies on the sector information being present in the DataFrame
# which is added during the data fetching stage in the dashboard file.

def calculate_pnl_snapshot(prices: Dict[str, pd.DataFrame], quantities: Dict[str, int]) -> pd.DataFrame:
    """
    Calculates the PnL snapshot (Start Price, End Price, PnL, Position Value)
    for each ticker in the portfolio based on the loaded price data.
    """
    pnl_data = []
    
    for ticker, df in prices.items():
        # Check that the DataFrame is not None, not empty, and has at least two data points 
        # (to calculate a change).
        if df is None or df.empty or len(df) < 2:
            print(f"Warning: Skipping {ticker}. Not enough data points ({len(df)}) to calculate PnL snapshot.")
            continue
            
        try:
            # Safely extract scalar values using .iloc[index] and .item()
            # This is where the failure often occurs due to index inconsistencies 
            # or unexpected data types. We keep .item() but rely on the size check above.
            
            # Use .item() to ensure we get a scalar number, handling NumPy dtypes
            start = float(df["Close"].iloc[0].item())
            end = float(df["Close"].iloc[-1].item())
            
            # We also ensure the values are valid numbers
            if pd.isna(start) or pd.isna(end):
                print(f"Warning: Skipping {ticker}. Start or End price is NaN.")
                continue

            qty = quantities.get(ticker, 0)
            weighted_pnl = (end - start) * qty
            position_value = end * qty
            pct = ((end - start) / start) * 100 if start != 0 else 0.0

            # Assuming 'Sector' is available 
            sector = df["Sector"].iloc[0] if "Sector" in df.columns else "Unknown"

            pnl_data.append({
                "Ticker": ticker,
                "Quantity": qty,
                "Start Price": start,
                "End Price": end,
                "PnL ($)": weighted_pnl,
                "Change (%)": pct,
                "Position Value ($)": position_value,
                "Sector": sector
            })
        except Exception as e:
            # CRITICAL: Print the error to the console for debugging
            print(f"Error: {ticker}: Failed PnL calculation due to exception: {e}. DataFrame head:\n{df['Close'].head()}")
            continue

    return pd.DataFrame(pnl_data)

def prepare_timeseries_data(prices: Dict[str, pd.DataFrame], quantities: Dict[str, int]) -> pd.DataFrame:
    """
    Prepares a concatenated DataFrame with time-series PnL and Position Value 
    for charting and advanced metrics calculation.
    """
    pnl_time_data = []
    for ticker, df in prices.items():
        if df is None or df.empty:
            continue
            
        try:
            ticker_df = df.copy()

            # Ensure the index is a DatetimeIndex
            if not isinstance(ticker_df.index, pd.DatetimeIndex):
                ticker_df.index = pd.to_datetime(ticker_df.index)
            
            qty = quantities.get(ticker, 0)
            ticker_df["Quantity"] = qty
            ticker_df["Price"] = ticker_df["Close"]
            ticker_df["Position Value ($)"] = ticker_df["Price"] * ticker_df["Quantity"]
            
            # PnL starts at 0, representing change from the beginning of the period
            ticker_df["PnL"] = (ticker_df["Price"] - ticker_df["Price"].iloc[0]) * ticker_df["Quantity"]
            ticker_df["Ticker"] = ticker
            ticker_df["Time"] = ticker_df.index
            
            pnl_time_data.append(
                ticker_df[["Time", "Ticker", "Quantity", "Price", "Position Value ($)", "PnL"]]
            )
        except Exception as e:
            print(f"Warning: {ticker}: Error building time series — {e}")

    if pnl_time_data:
        combined_df = pd.concat(pnl_time_data, ignore_index=True)
        return combined_df
    else:
        return pd.DataFrame()


def calculate_sector_allocation(df_pnl_snapshot: pd.DataFrame) -> Tuple[pd.DataFrame, float]:
    """
    Aggregates portfolio data by sector to determine allocation percentage.
    Returns the sector allocation DataFrame and the total portfolio value.
    """
    if df_pnl_snapshot.empty:
        return pd.DataFrame(), 0.0
        
    sector_df = df_pnl_snapshot[["Ticker", "Sector", "Position Value ($)"]].copy()

    # Aggregate by sector and collect tickers
    sector_alloc = (
        sector_df.groupby("Sector")
        .agg({
            "Position Value ($)": "sum",
            "Ticker": lambda s: ", ".join(sorted(set(s)))
        })
        .reset_index()
    )
    
    total_val = sector_alloc["Position Value ($)"].sum()
    
    if total_val > 0:
        # Add percentage for chart/table display
        sector_alloc["Percentage"] = (sector_alloc["Position Value ($)"] / total_val) * 100
        
    return sector_alloc, total_val