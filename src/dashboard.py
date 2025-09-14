# src/dashboard.py
"""
dashboard.py
============

Streamlit dashboard for monitoring intraday and historical Profit & Loss (PnL)
and portfolio risk metrics for multiple tickers.

Features
--------
- **Sidebar Controls**:
  - Input tickers (comma-separated).
  - Select historical data period and price interval.
  - Specify quantities per ticker.
  - Refresh data on demand.

- **Data Fetching**:
  - Retrieves market price data for the selected tickers using
    `ensure_prices` from `ensure_data.py`.
  - Caches data in `st.session_state` to avoid redundant fetches.

- **PnL & Position Metrics**:
  - Computes per-ticker PnL in absolute ($) and percentage terms.
  - Calculates position values based on latest prices and quantities.
  - Adds Quantity, Price, and Position Value ($) columns to all outputs.
  - Handles missing or invalid data gracefully.

- **Portfolio Summary**:
  - Displays total PnL, total position value, and total % change.
  - Shows a dynamic Portfolio Allocation pie chart by position value,
    which updates automatically based on current filters.

- **Visualization**:
  - Styled per-ticker PnL DataFrame with green/red highlighting for gains/losses.
  - Portfolio PnL Over Time line chart by ticker.
  - Portfolio Allocation pie chart (Altair) with tooltips.

- **Interactive PnL Table with CSV Export**:
  - Filter by ticker(s) and date range.
  - Shows filtered summary metrics (total/average PnL, position value, price).
  - Download filtered data as CSV (includes Quantity, Price, Position Value ($), and PnL) with dynamic filename.

Usage
-----
Run the dashboard with Streamlit:

    streamlit run src/dashboard.py

Dependencies
------------
- streamlit
- pandas
- altair
- ensure_data.ensure_prices

Notes
-----
Ensure that `ensure_data.py` is available and properly configured to fetch
market data before running this dashboard.
"""
import streamlit as st
import pandas as pd
import altair as alt
from ensure_data import ensure_prices

# --- Sidebar controls ---
st.sidebar.title("TradeSentinel Dashboard")
tickers = st.sidebar.text_input("Tickers (comma-separated)", "AAPL,MSFT,TSLA").split(",")
tickers = [t.strip() for t in tickers if t.strip()]
period = st.sidebar.selectbox(
    "Period",
    ["1d", "5d", "1mo", "3mo", "6mo", "1y", "ytd", "max"],
    index=1
)
interval = st.sidebar.selectbox(
    "Interval",
    ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"],
    index=5
)
qty_input = st.sidebar.text_input("Quantities (comma-separated)", "10,5,2")
refresh = st.sidebar.button("Refresh Data")

# --- Parse quantities ---
try:
    qty_list = [int(q.strip()) for q in qty_input.split(",") if q.strip()]
    if len(qty_list) != len(tickers):
        raise ValueError("Quantities count must match tickers count.")
    quantities = dict(zip(tickers, qty_list))
except Exception as e:
    st.error(f"Please enter valid integer quantities matching the number of tickers. Details: {e}")
    st.stop()

# --- Title ---
st.title("📈 TradeSentinel: Intraday PnL & Risk Monitor")

# --- Data Fetch ---
if refresh or "data" not in st.session_state:
    with st.spinner("Fetching market data..."):
        prices = ensure_prices(tickers, period=period, interval=interval)
        st.session_state.data = prices

# --- PnL Calculation (per ticker snapshot) ---
pnl_data = []
for ticker, df in st.session_state.data.items():
    if df is not None and not df.empty:
        try:
            # Use first and last Close for PnL snapshot
            start = float(df["Close"].iloc[0])
            end = float(df["Close"].iloc[-1])
            qty = quantities.get(ticker, 0)
            weighted_pnl = (end - start) * qty
            position_value = end * qty
            pct = ((end - start) / start) * 100 if start else 0.0
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

# --- Display Per-Ticker Table ---
if pnl_data:
    df_pnl = pd.DataFrame(pnl_data)
    st.subheader("📋 Per-Ticker PnL")
    st.dataframe(
        df_pnl.style.applymap(
            lambda v: "color: green" if isinstance(v, (int, float)) and v > 0 else ("color: red" if isinstance(v, (int, float)) and v < 0 else ""),
            subset=["PnL ($)", "Change (%)"]
        ),
        use_container_width=True
    )

    # --- Portfolio Summary + Pie Chart ---
    total_pnl = float(df_pnl["PnL ($)"].sum())
    total_value = float(df_pnl["Position Value ($)"].sum())
    total_pct = (total_pnl / total_value) * 100 if total_value else 0.0

    st.subheader("📊 Portfolio Summary")
    col1, col2 = st.columns([1, 1])

    with col1:
        st.metric("Total PnL ($)", f"${total_pnl:,.2f}")
        st.metric("Total Position Value ($)", f"${total_value:,.2f}")
        st.metric("Total Change (%)", f"{total_pct:.2f}%")

    with col2:
        pie_df = df_pnl[["Ticker", "Position Value ($)"]]
        if not pie_df.empty and pie_df["Position Value ($)"].sum() > 0:
            pie_chart = (
                alt.Chart(pie_df)
                .mark_arc()
                .encode(
                    theta=alt.Theta(field="Position Value ($)", type="quantitative", stack=True),
                    color=alt.Color(field="Ticker", type="nominal", legend=alt.Legend(title="Ticker")),
                    tooltip=[
                        alt.Tooltip("Ticker:N", title="Ticker"),
                        alt.Tooltip("Position Value ($):Q", title="Position Value ($)", format="$.2f")
                    ]
                )
                .properties(width=280, height=280, title="Portfolio Allocation")
            )
            st.altair_chart(pie_chart, use_container_width=True)
        else:
            st.info("No data available for pie chart.")

    # --- Portfolio PnL Over Time ---
    st.subheader("📉 Portfolio PnL Over Time")
    pnl_time_data = []
    for ticker, df in st.session_state.data.items():
        if df is not None and not df.empty:
            try:
                tmp = df.copy()
                qty = quantities.get(ticker, 0)
                tmp["Quantity"] = qty
                tmp["Price"] = tmp["Close"]
                tmp["Position Value ($)"] = tmp["Price"] * tmp["Quantity"]
                tmp["PnL"] = (tmp["Price"] - float(tmp["Price"].iloc[0])) * tmp["Quantity"]
                tmp["Ticker"] = ticker
                tmp["Time"] = tmp.index
                pnl_time_data.append(
                    tmp[["Time", "Ticker", "Quantity", "Price", "Position Value ($)", "PnL"]]
                )
            except Exception as e:
                st.warning(f"{ticker}: Error building time series — {e}")

    if pnl_time_data:
        combined_df = pd.concat(pnl_time_data, ignore_index=True)
        chart = (
            alt.Chart(combined_df)
            .mark_line()
            .encode(
                x=alt.X("Time:T", title="Time"),
                y=alt.Y("PnL:Q", title="PnL ($)"),
                color=alt.Color("Ticker:N", title="Ticker"),
            )
            .properties(width=700, height=400, title="Portfolio PnL Over Time by Ticker")
        )
        st.altair_chart(chart, use_container_width=True)

        # --- Interactive PnL Table with CSV Export ---
        st.subheader("🔍 Explore & Export PnL Data")
        tickers_selected = st.multiselect(
            "Select Ticker(s)",
            options=sorted(combined_df["Ticker"].unique().tolist()),
            default=sorted(combined_df["Ticker"].unique().tolist()),
        )
        date_min = combined_df["Time"].min().date()
        date_max = combined_df["Time"].max().date()
        date_range = st.date_input(
            "Select Date Range",
            value=(date_min, date_max),
            min_value=date_min,
            max_value=date_max,
        )

        filtered_df = combined_df[
            combined_df["Ticker"].isin(tickers_selected)
            & (combined_df["Time"].dt.date >= date_range[0])
            & (combined_df["Time"].dt.date <= date_range[1])
        ].copy()

        total_pnl_filtered = float(filtered_df["PnL"].sum()) if not filtered_df.empty else 0.0
        avg_pnl_filtered = float(filtered_df["PnL"].mean()) if not filtered_df.empty else 0.0
        total_value_filtered = float(filtered_df["Position Value ($)"].sum()) if not filtered_df.empty else 0.0
        avg_price_filtered = float(filtered_df["Price"].mean()) if not filtered_df.empty else 0.0

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total PnL (Filtered)", f"${total_pnl_filtered:,.2f}")
        with m2:
            st.metric("Average PnL (Filtered)", f"${avg_pnl_filtered:,.2f}")
        with m3:
            st.metric("Total Position Value (Filtered)", f"${total_value_filtered:,.2f}")
        with m4:
            st.metric("Average Price (Filtered)", f"${avg_price_filtered:,.2f}")

        st.dataframe(
            filtered_df.sort_values("Time").drop(columns=["Time"]),
            use_container_width=True,
        )

        # CSV export
        tickers_str = "_".join(tickers_selected) if tickers_selected else "All"
        filename = f"pnl_data_{tickers_str}_{date_range[0]}_{date_range[1]}.csv"
        csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="💾 Download filtered data as CSV",
            data=csv_data,
            file_name=filename,
            mime="text/csv"
        )
    else:
        st.info("No valid data to display. Try refreshing or adjusting tickers/period.")
else:
    st.info("No PnL data available. Please refresh to fetch data.")

# --- Conditional Shutdown Section ---
import os
import signal
import socket

# Detect if running locally by checking Streamlit's server address
server_addr = os.environ.get("STREAMLIT_SERVER_ADDRESS", "localhost")
if server_addr in ("localhost", "127.0.0.1"):
    st.divider()
    st.subheader("🛑 End Local Dashboard Session")
    st.write("✅ To exit: click the button below, then close this browser tab.")
    if st.button("Exit"):
        st.warning("✅ Dashboard shutdown initiated. Closing server...")
        pid = os.getpid()
        os.kill(pid, signal.SIGTERM)





