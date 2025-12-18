# src/portfolio_calculations.py
import pandas as pd
import streamlit as st

def calculate_pnl_data(prices: dict, quantities: dict) -> pd.DataFrame:
    """Calculates PnL and position snapshot data per ticker."""
    pnl_data = []
    for ticker, df in prices.items():
        if df is not None and not df.empty:
            try:
                start = df["close"].iloc[0]
                end = df["close"].iloc[-1]
                
                if hasattr(start, "item"): start = start.item()
                if hasattr(end, "item"): end = end.item()

                qty = quantities.get(ticker, 0)
                weighted_pnl = (end - start) * qty
                position_value = end * qty
                pct = ((end - start) / start) * 100 if start != 0 else 0.0
                
                sector = df["sector"].iloc[0] if "sector" in df.columns else "Unknown"

                pnl_data.append({
                    "Ticker": ticker,
                    "sector": sector,
                    "Quantity": qty,
                    "Start Price": start,
                    "End Price": end,
                    "PnL ($)": weighted_pnl,
                    "Change (%)": pct,
                    "Position Value ($)": position_value
                })
            except Exception as e:
                st.warning(f"{ticker}: Error calculating PnL — {e}")

    return pd.DataFrame(pnl_data) if pnl_data else pd.DataFrame()

def prepare_pnl_time_series(prices: dict, quantities: dict) -> pd.DataFrame:
    """Processes raw price data into a combined DataFrame for time series charting."""
    pnl_time_data = []
    for ticker, df in prices.items():
        if df is not None and not df.empty:
            try:
                tmp = df.copy()

                if not isinstance(tmp.index, pd.DatetimeIndex):
                    tmp.index = pd.to_datetime(tmp.index)
                
                qty = quantities.get(ticker, 0)
                tmp["Quantity"] = qty
                tmp["Price"] = tmp["close"]
                tmp["Position Value ($)"] = tmp["Price"] * tmp["Quantity"]
                tmp["PnL"] = (tmp["Price"] - tmp["Price"].iloc[0]) * tmp["Quantity"]
                tmp["Ticker"] = ticker
                tmp["Time"] = tmp.index
                
                pnl_time_data.append(
                    tmp[["Time", "Ticker", "Quantity", "Price", "Position Value ($)", "PnL"]]
                )
            except Exception as e:
                st.warning(f"{ticker}: Error building time series — {e}")

    return pd.concat(pnl_time_data, ignore_index=True) if pnl_time_data else pd.DataFrame()