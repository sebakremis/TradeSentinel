# pages/02_Portfolio_Sim.py
import streamlit as st
import pandas as pd
import altair as alt
import os
import signal
import plotly.express as px
import plotly.graph_objects as go
from ensure_data import ensure_prices

# Retrieve the data directly from session state
portfolio_tuples = st.session_state.get('portfolio', None)

# --- Title ---
st.title("📈 Simulated Portfolio Analysis")

 # --- Sidebar controls ---
st.sidebar.title("Set portfolio to analyze:")   

# Set table with simulated portfolio data
if portfolio_tuples:
    sim_portfolio = pd.DataFrame(portfolio_tuples, columns=['Ticker', 'Quantity'])
else:
    sim_portfolio = pd.DataFrame(columns=['Ticker', 'Quantity'])    
# Editable table for tickers and quantities
portfolio_df = st.sidebar.data_editor(
    sim_portfolio,
    num_rows="dynamic",  # allow adding/removing rows
    width="stretch"
)    
# --- Period & Interval selection with dynamic filtering ---

# Period selectbox (widget sets its own default via index)
period_input = st.sidebar.selectbox(
    "Period",
    ["1d", "5d", "1mo", "3mo", "6mo", "1y", "ytd", "max"],
    index=2,  # default to "1mo"
    key="active_period"
)

# Allowed intervals mapping
interval_map = {
    "1d":  ["1m", "5m", "15m", "30m", "1h"],
    "5d":  ["5m", "15m", "30m", "1h", "1d"],
    "1mo": ["15m", "30m", "1h", "1d", "1wk"],
    "3mo": ["15m", "30m", "1h", "1d", "1wk"],
    "6mo": ["1d", "1wk", "1mo"],
    "1y":  ["1d", "1wk", "1mo"],
    "ytd": ["1d", "1wk", "1mo"],
    "max": ["1d", "1wk", "1mo"]
}

interval_options = interval_map[period_input]

# Interval selectbox (widget sets its own default via index)
default_interval_index = (
    interval_options.index("30m") if period_input == "1d"
    else interval_options.index("1d")
)

interval_input = st.sidebar.selectbox(
    "Interval",
    interval_options,
    index=default_interval_index,
    key="active_interval"
)

# --- Refresh button ---
refresh = st.sidebar.button("Refresh Data")

# --- Static hint under the button (styled with italics) ---
st.sidebar.markdown(
    "💡 If you need **intraday** price data, choose an interval shorter than 1 day."
)

# --- On refresh, validate and commit parameters ---
if refresh:
    tickers_input = (
        portfolio_df["Ticker"].dropna().astype(str).str.strip().tolist()
    )
    quantities_input = portfolio_df["Quantity"]

    invalid_tickers = [t for t in tickers_input if not t or not t.replace('.', '').isalnum()]
    invalid_quantities = [q for q in quantities_input if pd.isna(q) or not isinstance(q, (int, float))]

    if invalid_tickers:
        st.sidebar.error(f"Invalid tickers: {', '.join(invalid_tickers)}")
    if invalid_quantities:
        st.sidebar.info(
            "Please fill in all quantities with numeric values, "
            "then press **Enter** to apply changes."
        )
    if invalid_tickers or invalid_quantities:
        st.stop()

    # Commit validated parameters to session_state
    st.session_state.active_tickers = tickers_input
    st.session_state.active_quantities = dict(
        zip(tickers_input, pd.Series(quantities_input).fillna(0).astype(int))
    )
    # Fetch and store data
    with st.spinner("Fetching market data..."):
        prices = ensure_prices(
            st.session_state.active_tickers,
            period=st.session_state.active_period,
            interval=st.session_state.active_interval,
        )
        st.session_state.data = prices

# --- Main content area ---
# --- Use stored parameters for display ---
if "active_tickers" in st.session_state:
    tickers = st.session_state.active_tickers
    quantities = st.session_state.active_quantities
    period = st.session_state.active_period
    interval = st.session_state.active_interval
else:
    st.info("Set your portfolio parameters and click **Refresh Data** to load the dashboard.")
    st.stop()

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
            start = df["Close"].iloc[0]
            if hasattr(start, "item"):
                start = start.item()
            end = df["Close"].iloc[-1]
            if hasattr(end, "item"):
                end = end.item()

            qty = quantities.get(ticker, 0)
            weighted_pnl = (end - start) * qty
            position_value = end * qty
            pct = ((end - start) / start) * 100 if start != 0 else 0.0

            pnl_data.append({
                "Ticker": ticker,
                "Quantity": qty,
                "Start Price": start,
                "End Price": end,
                "PnL ($)": weighted_pnl,
                "Change (%)": pct,
                "Position Value ($)": position_value
            })
        except Exception as e:
            st.warning(f"{ticker}: Error calculating PnL — {e}")

# --- Display Per-Ticker Table ---
if pnl_data:
    df_pnl = pd.DataFrame(pnl_data)

    st.subheader("📋 Per-Ticker PnL")

    # Display with conditional coloring + formatted floats
    st.dataframe(
        df_pnl.style
        .map(
            lambda v: "color: green" if isinstance(v, (int, float)) and v > 0
            else ("color: red" if isinstance(v, (int, float)) and v < 0 else ""),
            subset=["PnL ($)", "Change (%)"]
        )
        .format({
            "Quantity": "{:,.0f}",           # commas, no decimals
            "Start Price": "{:,.2f}",        # commas + 2 decimals
            "End Price": "{:,.2f}",          # commas + 2 decimals
            "PnL ($)": "{:,.2f}",            # commas + 2 decimals
            "Change (%)": "{:,.2f}",         # commas + 2 decimals
            "Position Value ($)": "{:,.2f}"  # commas + 2 decimals
        }),
        width="stretch"
    )




    # --- Portfolio Summary + Pie Chart ---
    total_pnl = df_pnl["PnL ($)"].sum()
    total_value = df_pnl["Position Value ($)"].sum()
    total_pct = (total_pnl / total_value) * 100 if total_value else 0.0

    st.subheader("📊 Portfolio Summary")
    col1, col2 = st.columns([1, 1])

    with col1:
        st.metric("Total PnL ($)", f"${total_pnl:,.2f}")
        st.metric("Total Position Value ($)", f"${total_value:,.2f}")
        st.metric("Total Change (%)", f"{total_pct:.2f}%")

    with col2:
        pie_df = df_pnl[["Ticker", "Position Value ($)"]].copy()
        total_value = pie_df["Position Value ($)"].sum()
    
        if not pie_df.empty and total_value > 0:          
    
            # Calculate percentage for labels
            pie_df["Percentage"] = (pie_df["Position Value ($)"] / total_value) * 100
    
            fig = px.pie(
                pie_df,
                names="Ticker",
                values="Position Value ($)",
                title=" ",
                hole=0.3  # optional: donut style
            )
    
            # Show ticker + percentage inside each slice
            fig.update_traces(textposition="inside", textinfo="percent+label")

            # Remove the side legend
            fig.update_layout(showlegend=False, title_x=0.3)
    
            st.plotly_chart(fig, width="stretch")
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
                tmp["PnL"] = (tmp["Price"] - tmp["Price"].iloc[0]) * tmp["Quantity"]
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
            .properties(width=700, height=400, title="")
        )
        st.altair_chart(chart)


        # --- Portfolio Allocation by Sector ---
        st.subheader("📊 Portfolio Allocation by Sector")
        
        latest_data = []
        for ticker, df in st.session_state.data.items():
            if df is not None and not df.empty:
                latest_close = df["Close"].iloc[-1]
                qty = quantities.get(ticker, 0)
                sector = df["Sector"].iloc[0] if "Sector" in df.columns else "Unknown"
                position_value = latest_close * qty
                latest_data.append({
                    "Ticker": ticker,
                    "Sector": sector,
                    "PositionValue": position_value
                })
        
        if latest_data:
            sector_df = pd.DataFrame(latest_data)
        
            # Aggregate by sector and collect tickers
            sector_alloc = (
                sector_df.groupby("Sector")
                .agg({
                    "PositionValue": "sum",
                    "Ticker": lambda s: ", ".join(sorted(set(s)))
                })
                .reset_index()
            )
        
            # Add percentage for table
            total_val = sector_alloc["PositionValue"].sum()
            sector_alloc["Percentage"] = (sector_alloc["PositionValue"] / total_val) * 100
        
            
            fig_sector = go.Figure(
                data=[
                    go.Pie(
                        labels=sector_alloc["Sector"],
                        values=sector_alloc["PositionValue"],
                        hole=0.3,
                        textinfo="percent+label",
                        textposition="inside",
                        hoverinfo="skip"  # ✅ disables hover entirely
                    )
                ]
            )
        
            fig_sector.update_layout(
                title="",   # no undefined title
                showlegend=False,
                title_x=0.3,
                margin=dict(l=10, r=10, t=60, b=10)
            )
            
            # Show chart first
            st.plotly_chart(fig_sector, width='stretch')
            
            # Then show the simplified table below (only Sector + Ticker, no index, no percentage)
            st.dataframe(
                sector_alloc[["Sector", "Ticker"]],
                width='stretch',
                hide_index=True
            )

        else:
            st.info("No data available for sector allocation chart.")



      
        # --- Advanced Metrics Section ---
        from metrics import (
            calculate_var, calculate_cvar, sharpe_ratio, sortino_ratio,
            calmar_ratio, max_drawdown, correlation_matrix, win_loss_stats
        )

        st.subheader("📊 Advanced Metrics")

        # Portfolio returns (daily or per interval)
        portfolio_values = combined_df.groupby("Time")["Position Value ($)"].sum()
        portfolio_returns = portfolio_values.pct_change().dropna()
        cum_returns = (1 + portfolio_returns).cumprod()

        # Risk & performance metrics
        var_95 = calculate_var(portfolio_returns, 0.95)
        cvar_95 = calculate_cvar(portfolio_returns, 0.95)
        sharpe = sharpe_ratio(portfolio_returns)
        sortino = sortino_ratio(portfolio_returns)
        calmar = calmar_ratio(portfolio_returns)
        mdd = max_drawdown(cum_returns)

        # Win/loss stats from PnL column
        win_loss = win_loss_stats(combined_df["PnL"])

        # Display metrics in columns
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("VaR (95%)", f"{var_95:.2%}")
            st.metric("CVaR (95%)", f"{cvar_95:.2%}")
        with col2:
            st.metric("Sharpe Ratio", f"{sharpe:.2f}")
            st.metric("Sortino Ratio", f"{sortino:.2f}")
        with col3:
            st.metric("Calmar Ratio", f"{calmar:.2f}")
            st.metric("Max Drawdown", f"{mdd:.2%}")

        
        # --- Asset Correlation Matrix (Styled Table) ---
        st.subheader("📈 Asset Correlation Matrix")

        # Pivot to get one column per asset
        price_wide = combined_df.pivot(index="Time", columns="Ticker", values="Price")

        # Compute correlation matrix and round to 6 decimals
        corr_df = correlation_matrix(price_wide).round(6)

        # Display with conditional formatting
        st.dataframe(
            corr_df.style.background_gradient(cmap="coolwarm", vmin=-1, vmax=1)
)
  
                
        # --- Editable Table: Interactive PnL Table with CSV Export ---

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
        
        if not filtered_df.empty:
            total_pnl_filtered = filtered_df["PnL"].sum()
            avg_pnl_filtered = filtered_df["PnL"].mean()
            total_value_filtered = filtered_df["Position Value ($)"].sum()
            avg_price_filtered = filtered_df["Price"].mean()
        
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Total PnL (Filtered)", f"${total_pnl_filtered:,.2f}")
            with m2:
                st.metric("Average PnL (Filtered)", f"${avg_pnl_filtered:,.2f}")
            with m3:
                st.metric("Total Position Value (Filtered, M$)", f"{total_value_filtered/1_000_000:,.2f} M")
            with m4:
                st.metric("Average Price (Filtered)", f"${avg_price_filtered:,.2f}")
        
            # Sort so most recent entries appear first
            df_display = filtered_df.sort_values("Time", ascending=False).copy()


           # Split into Date and Time columns
            df_display["Date"] = df_display["Time"].dt.strftime("%Y-%m-%d")
            df_display["Time"] = df_display["Time"].dt.strftime("%H:%M:%S")  # overwrite with clean 'Time'
            
            # Reorder so Date/Time appear first
            cols = ["Date", "Time"] + [c for c in df_display.columns if c not in ["Date", "Time"]]
            df_display = df_display[cols].reset_index(drop=True)
            
            # --- Round numeric columns to 2 decimals ---
            for col in ["Price", "Position Value ($)", "PnL"]:
                if col in df_display.columns:
                    df_display[col] = df_display[col].astype(float).round(2)


            # --- Round numeric columns to 2 decimals ---
            for col in ["Price", "Position Value ($)", "PnL"]:
                if col in df_display.columns:
                    df_display[col] = df_display[col].astype(float).round(2)
            
            # --- Display with formatted view (but keep numeric for CSV) ---
            st.dataframe(
                df_display.style.format({
                    "Quantity": "{:,.0f}",          # commas, no decimals
                    "Price": "{:,.2f}",             # commas + 2 decimals
                    "PnL": "{:,.2f}",               # commas + 2 decimals
                    "Position Value ($)": "{:,.2f}" # commas + 2 decimals
                }),
                width="stretch",
                hide_index=True
            )


       
            # CSV export
            tickers_str = "_".join(tickers_selected) if tickers_selected else "All"
            filename = f"pnl_data_{tickers_str}_{date_range[0]}_{date_range[1]}.csv"
            csv_data = df_display.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="💾 Download filtered data as CSV",
                data=csv_data,
                file_name=filename,
                mime="text/csv",
            )
        else:
            st.info("No valid data to display. Try refreshing or adjusting tickers/period.")
        
        # --- end of block ---


# Credits
st.markdown("---")
st.markdown(
    "🔗 [View Source Code on GitHub](https://github.com/sebakremis/TradeSentinel)",
    unsafe_allow_html=True
)
st.caption("Built using Streamlit and Python.")
# Use st.switch_page for proper navigation
if st.button("Go back to Market View"):
    st.switch_page("main.py")