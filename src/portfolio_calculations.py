# src/portfolio_calculations.py
import pandas as pd
import streamlit as st

def calculate_pnl_data(prices: dict, quantities: dict) -> pd.DataFrame:
    """Calculates PnL, Dividends, and position snapshot data per ticker."""
    pnl_data = []
    
    for ticker, df in prices.items():
        if df is not None and not df.empty:
            try:
                # 1. Get Prices
                start = df["close"].iloc[0]
                end = df["close"].iloc[-1]
                
                # Safe conversion for single values
                if hasattr(start, "item"): start = start.item()
                if hasattr(end, "item"): end = end.item()

                qty = quantities.get(ticker, 0)
                
                # 2. Calculate Price PnL (Capital Gains)
                price_pnl = (end - start) * qty
                
                # 3. Calculate Dividends
                if 'dividends' in df.columns:
                    div_per_share = df['dividends'].sum()
                else:
                    div_per_share = 0.0
                
                total_div_payout = div_per_share * qty

                # 4. Calculate Totals and Metadata
                position_value = end * qty
                total_return = price_pnl + total_div_payout
                pct_change = ((end - start) / start) * 100 if start != 0 else 0.0
                
                sector = df["sector"].iloc[0] if "sector" in df.columns else "Unknown"

                pnl_data.append({
                    "Ticker": ticker,
                    "sector": sector,
                    "Quantity": qty,
                    "Start Price": start,
                    "End Price": end,
                    "PnL ($)": price_pnl,          # Price appreciation only
                    "Dividends ($)": total_div_payout, # Dividends payout
                    "Total Return ($)": total_return,  # Price PnL + Dividends
                    "Change (%)": pct_change,
                    "Position Value ($)": position_value
                })
            except Exception as e:
                print(f"{ticker}: Error calculating PnL — {e}")

    return pd.DataFrame(pnl_data) if pnl_data else pd.DataFrame()

def prepare_pnl_time_series(prices: dict, quantities: dict) -> pd.DataFrame:
    """Processes raw price data into a combined DataFrame for time series charting and export."""
    pnl_time_data = []
    
    for ticker, df in prices.items():
        if df is not None and not df.empty:
            try:
                tmp = df.copy()

                # Ensure datetime index
                if not isinstance(tmp.index, pd.DatetimeIndex):
                    tmp.index = pd.to_datetime(tmp.index)
                
                qty = quantities.get(ticker, 0)
                tmp["Quantity"] = qty
                tmp["Price"] = tmp["close"]
                
                # Standard Metrics
                tmp["Position Value ($)"] = tmp["Price"] * tmp["Quantity"]
                tmp["PnL"] = (tmp["Price"] - tmp["Price"].iloc[0]) * tmp["Quantity"]
                
                # --- Dividend Handling ---
                # Check for 'dividends' or 'Dividends' (standard yfinance)
                if 'dividends' in tmp.columns:
                    # Calculate Total Cash Payout = Per Share Dividend * Quantity
                    tmp["Dividends"] = tmp["dividends"].fillna(0) * qty
                elif 'Dividends' in tmp.columns:
                    tmp["Dividends"] = tmp["Dividends"].fillna(0) * qty
                else:
                    tmp["Dividends"] = 0.0

                tmp["Ticker"] = ticker
                tmp["Time"] = tmp.index
                
                # Select columns for final output
                # Added "Dividends" to the list
                pnl_time_data.append(
                    tmp[["Time", "Ticker", "Quantity", "Price", "Position Value ($)", "PnL", "Dividends"]]
                )
            except Exception as e:
                st.warning(f"{ticker}: Error building time series — {e}")

    return pd.concat(pnl_time_data, ignore_index=True) if pnl_time_data else pd.DataFrame()