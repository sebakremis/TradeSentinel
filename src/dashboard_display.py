# src/dashboard_display.py
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt

from src.metrics import (
    calculate_var, calculate_cvar, sharpe_ratio, sortino_ratio,
    calmar_ratio, max_drawdown, correlation_matrix, win_loss_stats
)

def display_per_ticker_pnl(df_pnl: pd.DataFrame):
    """Displays the per-ticker PnL table with conditional formatting."""
    st.subheader("📋 Per-Ticker PnL")

    st.dataframe(
        df_pnl.sort_values(by='PnL ($)', ascending=False)
        .style
        .map(
            lambda v: "color: green" if isinstance(v, (int, float)) and v > 0
            else ("color: red" if isinstance(v, (int, float)) and v < 0 else ""),
            subset=["PnL ($)", "Change (%)"]
        )
        .format({
            "Quantity": "{:,.0f}",
            "Start Price": "{:,.2f}",
            "End Price": "{:,.2f}",
            "PnL ($)": "{:,.2f}",
            "Change (%)": "{:,.2f}",
            "Position Value ($)": "{:,.2f}"
        })
        .hide(subset=["Sector"], axis=1),
        width="stretch",
        hide_index=True
    )

def display_portfolio_summary(df_pnl: pd.DataFrame):
    """Calculates and displays the overall portfolio summary metrics and a pie chart."""
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
            pie_df["Percentage"] = (pie_df["Position Value ($)"] / total_value) * 100
    
            fig = px.pie(
                pie_df,
                names="Ticker",
                values="Position Value ($)",
                title=" ",
                hole=0.3
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(showlegend=False, title_x=0.3)
    
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No data available for portfolio value pie chart.")




def display_pnl_over_time(combined_df: pd.DataFrame):
    """Displays the portfolio PnL over time chart."""
    st.subheader("📉 Portfolio PnL Over Time")
    
    if not combined_df.empty:
        chart = (
            alt.Chart(combined_df)
            .mark_line()
            .encode(
                x=alt.X("Time:T", title="Time"),
                y=alt.Y("PnL:Q", title="PnL ($)"),
                color=alt.Color("Ticker:N", title="Ticker"),
                tooltip=["Time:T", "Ticker:N", alt.Tooltip("PnL:Q", format="$,.2f")]
            )
            .properties(width=700, height=400, title="Portfolio PnL by Ticker")
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No time series data available for charting.")


def display_sector_allocation(df_pnl: pd.DataFrame):
    """Displays the portfolio allocation by sector using a pie chart and table."""
    st.subheader("📊 Portfolio Allocation by Sector")
    
    sector_alloc = (
        df_pnl.groupby("Sector")
        .agg({
            "Position Value ($)": "sum",
            "Ticker": lambda s: ", ".join(sorted(set(s)))
        })
        .reset_index()
        .rename(columns={"Position Value ($)": "PositionValue"})
    )
    
    if not sector_alloc.empty and sector_alloc["PositionValue"].sum() > 0:
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
                    hovertemplate="<b>%{label}</b><br>Value: $%{value:,.2f}<extra></extra>"
                )
            ]
        )
        
        fig_sector.update_layout(
            title="",
            showlegend=False,
            margin=dict(l=10, r=10, t=60, b=10)
        )
        
        st.plotly_chart(fig_sector, use_container_width=True)
        
        st.dataframe(
            sector_alloc[["Sector", "PositionValue", "Ticker"]]
            .rename(columns={"PositionValue": "Position Value ($)"})
            .style.format({"Position Value ($)": "${:,.2f}"}),
            width='stretch',
            hide_index=True
        )
    else:
        st.info("No data available for sector allocation chart.")

def display_advanced_metrics(combined_df: pd.DataFrame):
    """Calculates and displays advanced portfolio risk and performance metrics."""
    st.subheader("📊 Advanced Metrics")

    if combined_df.empty:
        st.info("No data available to calculate advanced metrics.")
        return

    portfolio_values = combined_df.groupby("Time")["Position Value ($)"].sum()
    portfolio_returns = portfolio_values.pct_change().dropna()
    
    if portfolio_returns.empty:
        st.warning("Not enough data points to calculate returns for advanced metrics.")
        return

    cum_returns = (1 + portfolio_returns).cumprod()

    # Risk & performance metrics
    var_95 = calculate_var(portfolio_returns, 0.95)
    cvar_95 = calculate_cvar(portfolio_returns, 0.95)
    sharpe = sharpe_ratio(portfolio_returns)
    sortino = sortino_ratio(portfolio_returns)
    calmar = calmar_ratio(portfolio_returns)
    mdd = max_drawdown(cum_returns)

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
        
    st.subheader("📈 Asset Correlation Matrix")

    price_wide = combined_df.pivot(index="Time", columns="Ticker", values="Price")
    corr_df = correlation_matrix(price_wide).round(4)

    st.dataframe(
        corr_df.style.background_gradient(cmap="coolwarm", vmin=-1, vmax=1).format("{:,.4f}")
    )


def display_export_table(combined_df: pd.DataFrame):
    """Displays an interactive, filterable table for PnL data with CSV export."""
    st.subheader("🔍 Export PnL Data")
    
    if combined_df.empty:
        st.info("No data available for export.")
        return

    tickers_selected = st.multiselect(
        "Select Ticker(s)",
        options=sorted(combined_df["Ticker"].unique().tolist()),
        default=sorted(combined_df["Ticker"].unique().tolist()),
    )
    
    date_min = combined_df["Time"].min().normalize().date()
    date_max = combined_df["Time"].max().normalize().date()
    
    date_range = st.date_input(
        "Select Date Range",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
    )
    
    if len(date_range) != 2:
        st.warning("Please select a valid date range.")
        return

    filtered_df = combined_df[
        combined_df["Ticker"].isin(tickers_selected)
        & (combined_df["Time"].dt.date >= date_range[0])
        & (combined_df["Time"].dt.date <= date_range[1])
    ].copy()
    
    if not filtered_df.empty:
        
        df_display = filtered_df.sort_values("Time", ascending=False).copy()

        df_display["Date"] = df_display["Time"].dt.strftime("%Y-%m-%d")
        df_display["Time_of_Day"] = df_display["Time"].dt.strftime("%H:%M:%S")
        
        df_display = df_display.drop(columns=["Time"], errors='ignore')

        cols_order = ["Date", "Time_of_Day", "Ticker", "Quantity", "Price", "Position Value ($)", "PnL"]
        df_display = df_display[[c for c in cols_order if c in df_display.columns]].reset_index(drop=True)
        
        for col in ["Price", "Position Value ($)", "PnL"]:
            if col in df_display.columns:
                df_display[col] = df_display[col].astype(float).round(2)

        st.dataframe(
            df_display.style.format({
                "Quantity": "{:,.0f}",
                "Price": "{:,.2f}",
                "PnL": "{:,.2f}",
                "Position Value ($)": "{:,.2f}"
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
            key="download_pnl_csv"
        )
    else:
        st.info("No valid data to display. Try refreshing or adjusting tickers/date range.")