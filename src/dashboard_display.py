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
from src.indicators import annualized_risk_free_rate

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
        .hide(subset=["sector"], axis=1),
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

            st.plotly_chart(fig, width='stretch')
 
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
        st.altair_chart(chart, width='stretch')
    else:
        st.info("No time series data available for charting.")


def display_sector_allocation(df_pnl: pd.DataFrame):
    """Displays the portfolio allocation by sector using a pie chart and table."""
    st.subheader("📊 Portfolio Allocation by Sector")
    
    sector_alloc = (
        df_pnl.groupby("sector")
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
                    labels=sector_alloc["sector"],
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
        
        st.plotly_chart(fig_sector, width='stretch')
        
        st.dataframe(
            sector_alloc[["sector", "PositionValue", "Ticker"]]
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

def highlight_change(value):
    """
    Returns the CSS style string for background color based on the value.
    Green for positive, Red for negative.
    """
    if pd.isna(value):
        return ''
    elif value > 0:
        return 'color: green; font-weight: bold;'
    elif value < 0:
        return 'color: red; font-weight: bold;'
    else:
        return ''

def display_period_selection()-> dict:
    """Displays the period selection UI and returns the selected period argument."""
    # Define selectable periods
    AVAILABLE_PERIODS = ["3mo", "6mo", "ytd", "1y", "2y", "5y", "Custom Date"]

    with st.sidebar:
        st.header("📅 Configuration")
        
        # Period Selection
        selected_period = st.selectbox(
            "Lookback Period", 
            options=AVAILABLE_PERIODS, 
            index=AVAILABLE_PERIODS.index("2y"), # Default to 2 years
            key='data_period_select'
        )
        # Initialize the dictionary to hold fetch arguments
        fetch_kwargs = {}
        
        if selected_period == "Custom Date":
            today = pd.Timestamp.now().normalize()
            default_start_date = today - pd.DateOffset(years=2)
            
            col1, col2 = st.columns(2)
            with col1:
                # Custom Start Date Selection
                start_date = st.date_input(
                    "Select **Start Date**", 
                    value=default_start_date,
                    max_value=today,
                    key='custom_start'
                )        
            with col2:
                # Custom End Date Selection (Default to Today)
                end_date = st.date_input(
                    "Select **End Date**", 
                    value=today,
                    min_value=start_date, # End date cannot be before start date
                    max_value=today,
                    key='custom_end'
                )
            # Logic for Custom Date
            fetch_kwargs['start'] = str(start_date)
            fetch_kwargs['end'] = str(end_date)
            fetch_kwargs['period'] = None

        else:
            # Logic for Standard Periods
            fetch_kwargs['period'] = selected_period
            fetch_kwargs['start'] = None
            fetch_kwargs['end'] = None
    
    return fetch_kwargs

def display_risk_return_plot(final_df: pd.DataFrame):
    """Renders the risk-return scatter plot."""
    st.subheader("Historical Risk-Return")

    if not final_df.empty and 'avgReturn' in final_df.columns and 'annualizedVol' in final_df.columns:
        # Create the scatter plot using Altair
        chart = alt.Chart(final_df).mark_point(size=100).encode(
            x=alt.X('annualizedVol', title='Annualized Volatility (Vol%)'),
            y=alt.Y('avgReturn', title='Annualized Average Return (AAR%)'),
            tooltip=['Ticker', 'avgReturn', 'annualizedVol'],
            color=alt.Color('Ticker', legend=None)
        ).properties(
            title=''
        ).interactive()

        st.altair_chart(chart, width='stretch')
    else:
        st.warning("Cannot generate risk-return plot. Ensure tickers are selected and data is loaded.")

def display_info_section(df_daily: pd.DataFrame):
    """
    Displays the informational sidebar section with trading period info.
    """
    if not df_daily.empty and 'Date' in df_daily.columns:
        num_days = df_daily['Date'].nunique()
        first_date = pd.to_datetime(df_daily['Date'].min())
        last_date = pd.to_datetime(df_daily['Date'].max())
    else:
        num_days = 0
        first_date, last_date = None, None

    with st.sidebar.expander("ℹ️ Trading Period Info", expanded=True):
        st.write(f"**Trading Days:** {num_days}")
        st.write(f"**First Price Date:** {first_date.strftime('%Y-%m-%d') if first_date else 'N/A'}")
        st.write(f"**Last Price Date:** {last_date.strftime('%Y-%m-%d') if last_date else 'N/A'}")
        st.write(f"**Annualized Risk Free rate:** {annualized_risk_free_rate*100:.2f}% (assumed risk-free rate for Sharpe Ratio calculation)")


def display_guides_section():
    """
    Displays the informational sidebar section with guides on calculations and usage.
    """
    st.sidebar.markdown("---")  
    with st.sidebar.expander("ℹ️ Guides", expanded=False):        
        st.subheader("How calculations are made")
        st.subheader("Data Source & Lookback Period")
        st.markdown(
            """
            The data is sourced via an external financial data API (Yahoo Finance). 
            
            - **Data Type:** Daily Adjusted Closing Prices (`Close`), along with Sector and Dividend Payout.
            """
        )

        st.subheader("Summary Table Column Methodology")
        
        st.markdown("**1. First**")
        st.info("The Adjusted Close Price on the **first day** of the selected Lookback Period. Used as the base for all period-related returns")
        
        st.markdown("**2. Last**")
        st.info("The latest Adjusted Close Price.")      
        
        st.markdown("**3. Dividends**")
        st.info("The **Total Sum of Dividends** paid out per share for the stock over the entire Lookback Period.")
        

        st.markdown("**4. Forecast High / Forecast Low**")
        st.info("The max/min price forecast range based on MonteCarlo simulation for a 1 month time horizon.")
        
        st.markdown("**5. Avg Return (AAR%) / Annualized Vol (Vol%)**")
        st.info("These metrics are calculated using the daily logarithmic returns over the Lookback Period and are then **annualized** for comparison (assumes 252 trading days/year).")
        
        st.markdown("**6. Sharpe Ratio**")
        st.info("Calculated as the **Annualized Average Return** (AAR%) divided by the **Annualized Volatility** (Vol%). This is a key measure of risk-adjusted return (assumes a risk-free rate of 0% for simplicity in this demo).")
        
        st.markdown("---")
        st.subheader("How to use the dashboard")
        st.markdown("""
        1. **Choose Lookback Period** for analysis (e.g., '1y' or 'Custom Date').
        2. **View Historical Risk-Return** chart for followed tickers.  
        3. **View Metrics summary** table.
        4. **Select Tickers** in the table and click **Simulate Portfolio** to analyze an equally-weighted $100k portfolio.
        5. **Manage Tickers**: Add or remove tickers to follow below.
        """)

def display_credits():
    """Displays the credits section."""
    st.markdown("---")
    st.markdown(
        "🔗 [View Source Code on GitHub](https://github.com/sebakremis/TradeSentinel)",
        unsafe_allow_html=True
    )
    st.markdown("👤 Developed by Sebastian Kremis")
    st.caption("Built using Streamlit and Python. NO investment advice. For educational/demo purposes only.")