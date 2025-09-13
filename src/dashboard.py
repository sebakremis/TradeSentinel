# src/dashboard.py
import streamlit as st
import pandas as pd
import altair as alt
from ensure_data import ensure_prices

# --- Sidebar controls ---
st.sidebar.title("TradeSentinel Dashboard")
tickers = st.sidebar.text_input("Tickers (comma-separated)", "AAPL,MSFT,TSLA").split(",")
period = st.sidebar.selectbox("Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "ytd", "max"], index=1)
interval = st.sidebar.selectbox("Interval", ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"], index=5)
qty_input = st.sidebar.text_input("Quantities (comma-separated)", "10,5,2")
refresh = st.sidebar.button("Refresh Data")

# --- Parse quantities ---
try:
    quantities = dict(zip([t.strip() for t in tickers], map(int, qty_input.split(","))))
except ValueError:
    st.error("Please enter valid integer quantities matching the number of tickers.")
    st.stop()

# --- Title ---
st.title("📈 TradeSentinel: Intraday PnL & Risk Monitor")

# --- Data Fetch ---
if refresh or "data" not in st.session_state:
    with st.spinner("Fetching market data..."):
        prices = ensure_prices(tickers, period=period, interval=interval)
        st.session_state.data = prices

# --- PnL Calculation ---
pnl_data = []
for ticker, df in st.session_state.data.items():
    if df is not None and not df.empty:
        try:
            start = df["Close"].iloc[0].item()
            end = df["Close"].iloc[-1].item()
            qty = quantities.get(ticker.strip(), 0)
            weighted_pnl = (end - start) * qty
            position_value = end * qty
            pct = ((end - start) / start) * 100

            pnl_data.append({
                "Ticker": ticker,
                "Quantity": qty,
                "Start Price": round(start, 2),
                "End Price": round(end, 2),
                "PnL ($)": round(weighted_pnl, 2),
                "Change (%)": round(pct, 2),
                "Position Value ($)": round(position_value, 2)
            })
        except Exception as e:
            st.warning(f"{ticker}: Error calculating PnL — {e}")

# --- Display Table ---
if pnl_data:
    df_pnl = pd.DataFrame(pnl_data)
    st.subheader("📋 Per-Ticker PnL")
    st.dataframe(df_pnl.style.applymap(
        lambda v: "color: green" if isinstance(v, float) and v > 0 else "color: red",
        subset=["PnL ($)", "Change (%)"]
    ))

    # --- Portfolio Summary ---
    total_pnl = df_pnl["PnL ($)"].sum()
    total_value = df_pnl["Position Value ($)"].sum()
    total_pct = (total_pnl / total_value) * 100 if total_value else 0
    st.subheader("📊 Portfolio Summary")
    st.metric("Total PnL ($)", f"{total_pnl:.2f}")
    st.metric("Total Position Value ($)", f"{total_value:.2f}")
    st.metric("Total Change (%)", f"{total_pct:.2f}%")

    # --- Optional Chart ---
    st.subheader("📈 Weighted PnL by Ticker")
    st.bar_chart(df_pnl.set_index("Ticker")["PnL ($)"])

    # --- Additional Charts ---
    st.subheader("📉 Portfolio PnL Over Time")
    # Build a combined DataFrame for all tickers
    pnl_time_data = []
    for ticker, df in st.session_state.data.items():
        if df is not None and not df.empty:
            df = df.copy()
            df["PnL"] = (df["Close"] - df["Close"].iloc[0]) * quantities.get(ticker.strip(), 0)
            df["Ticker"] = ticker
            df["Time"] = df.index
            pnl_time_data.append(df[["Time", "PnL", "Ticker"]])

    if pnl_time_data:
        combined_df = pd.concat(pnl_time_data)

        chart = alt.Chart(combined_df).mark_line().encode(
            x=alt.X("Time:T", title="Time"),
            y=alt.Y("PnL:Q", title="PnL ($)"),
            color=alt.Color("Ticker:N", title="Ticker")
        ).properties(
            width=700,
            height=400,
            title="Portfolio PnL Over Time by Ticker"
        )

        st.altair_chart(chart, use_container_width=True)
    
else:
    st.info("No valid data to display. Try refreshing or adjusting tickers/period.")


# Shutdown button
import os
import signal
import streamlit as st

st.divider()
st.subheader("🛑 Exit Dashboard")
st.write("Click the button below then close the tab. If running locally, this will also stop the server in your terminal.")
if st.button("Exit"):
    st.warning("✅ Dashboard shutdown initiated. Closing server...")

    # Get the current process ID
    pid = os.getpid()

    # Send SIGTERM to the current process
    os.kill(pid, signal.SIGTERM)


