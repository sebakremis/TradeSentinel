"""
src/dashboard_display.py

This module centralizes reusable rendering functions for dashboard sections that
are shared across multiple pages of the TradeSentinel project. Functions in this
file follow the naming convention `display_{function_name}`, indicating that they
are generic, composable display utilities intended to be imported and reused
wherever needed.

By contrast, rendering logic that is unique to a specific page remains defined
within that page's module, using the naming convention `_render_{function_name}`.
This separation ensures:
    - Clear distinction between shared vs. page-specific rendering code
    - Improved modularity and maintainability of the dashboard layer
    - Consistent naming conventions that make the scope and reusability of each
      function immediately apparent

In short, `display_*` functions = reusable building blocks,
while `_render_*` functions = page-specific implementations.
"""

import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt
from src.config import (
    RISK_FREE_RATE, FORECAST_HORIZON, BENCHMARK_INDEX,
    DEFAULT_LOOKBACK_PERIOD, FIXED_INTERVAL
)
from src.analytics import (
    calculate_var, calculate_cvar, sharpe_ratio, sortino_ratio,
    calmar_ratio, max_drawdown, correlation_matrix, win_loss_stats
)


def display_per_ticker_pnl(df_pnl: pd.DataFrame):
    """Displays the per-ticker PnL table with conditional formatting."""
    st.subheader("📋 Per-Ticker PnL")

    # Define the specific column order for the table
    # We check if columns exist first to ensure safety if you revert to old data
    desired_order = [
        "Ticker", "Quantity", "Start Price", "End Price", 
        "PnL ($)", "Dividends ($)", "Total Return ($)", 
        "Change (%)", "Position Value ($)"
    ]
    
    # Filter to only use columns that actually exist in the dataframe
    final_cols = [c for c in desired_order if c in df_pnl.columns]

    st.dataframe(
        df_pnl[final_cols].sort_values(by='PnL ($)', ascending=False)
        .style
        .map(
            lambda v: "color: green" if isinstance(v, (int, float)) and v > 0
            else ("color: red" if isinstance(v, (int, float)) and v < 0 else ""),
            # Apply color logic to PnL, Total Return, and Change %
            subset=[c for c in ["PnL ($)", "Total Return ($)", "Change (%)"] if c in df_pnl.columns]
        )
        .format({
            "Quantity": "{:,.0f}",
            "Start Price": "{:,.2f}",
            "End Price": "{:,.2f}",
            "PnL ($)": "{:,.2f}",
            "Dividends ($)": "{:,.2f}",    
            "Total Return ($)": "{:,.2f}", 
            "Change (%)": "{:,.2f}",
            "Position Value ($)": "{:,.2f}"
        }),
        width="stretch",
        hide_index=True
    )

def display_portfolio_summary(df_pnl: pd.DataFrame):
    """Calculates and displays the overall portfolio summary metrics and a pie chart."""
    
    # 1. Calculate Totals
    total_price_pnl = df_pnl["PnL ($)"].sum()
    total_value = df_pnl["Position Value ($)"].sum()
    
    # Sum Dividends and Total Return if they exist 
    total_divs = df_pnl["Dividends ($)"].sum() if "Dividends ($)" in df_pnl.columns else 0.0
    total_return = df_pnl["Total Return ($)"].sum() if "Total Return ($)" in df_pnl.columns else total_price_pnl

    # 2. Calculate ROI %
    # Cost Basis = Current Value - Capital Gains (Price PnL)
    cost_basis = total_value - total_price_pnl
    total_return_pct = (total_return / cost_basis) * 100 if cost_basis != 0 else 0.0

    st.subheader("📊 Portfolio Summary")
    col1, col2 = st.columns([1, 1])

    # --- Metrics Section ---
    with col1:
        # Main high-level metrics
        st.metric("Total Position Value ($)", f"${total_value:,.2f}")
        
        # Total Return (Combines Price PnL + Dividends)
        st.metric(
            "Total Return ($)", 
            f"${total_return:,.2f}", 
            f"{total_return_pct:.2f}%", 
            help="Includes both Capital Gains and Dividends"
        )
        
        st.markdown("---") # Visual separator for the breakdown
        
        # Breakdown: Capital Gains vs Dividends
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.metric("Capital Gains", f"${total_price_pnl:,.2f}")
        with m_col2:
            st.metric("Total Dividends", f"${total_divs:,.2f}")

    # --- Chart Section (Unchanged logic, just cleanup) ---
    with col2:
        pie_df = df_pnl[["Ticker", "Position Value ($)"]].copy()
        
        if not pie_df.empty and pie_df["Position Value ($)"].sum() > 0:
            fig = px.pie(
                pie_df,
                names="Ticker",
                values="Position Value ($)",
                title="Allocation by Value",
                hole=0.4
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(
                showlegend=False, 
                title_x=0.3,
                margin=dict(t=30, b=0, l=0, r=0) # Tighter margins
            )

            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No positive position value to display.")


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
    
    # Check if 'Time' exists, otherwise handle gracefully (though it should exist based on context)
    if "Time" not in combined_df.columns:
        st.error("Dataframe missing 'Time' column required for filtering.")
        return

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

        # Updated columns order to include Dividends
        # We check for both "Dividends" and "Dividend" to be safe
        possible_div_cols = [c for c in df_display.columns if "ividend" in c]
        div_col = possible_div_cols[0] if possible_div_cols else "Dividends"

        cols_order = ["Date", "Ticker", "Quantity", "Price", "Position Value ($)", "PnL", div_col]
        
        # Filter to only use columns that actually exist
        final_cols = [c for c in cols_order if c in df_display.columns]
        df_display = df_display[final_cols].reset_index(drop=True)
        
        # Format numeric columns
        numeric_cols = ["Price", "Position Value ($)", "PnL", div_col]
        for col in numeric_cols:
            if col in df_display.columns:
                df_display[col] = df_display[col].fillna(0.0).astype(float).round(2)

        st.dataframe(
            df_display.style.format({
                "Quantity": "{:,.0f}",
                "Price": "{:,.2f}",
                "PnL": "{:,.2f}",
                "Position Value ($)": "{:,.2f}",
                div_col: "{:,.2f}" # Format dividends
            }),
            width="stretch",
            hide_index=True
        )
        
        # CSV export
        tickers_str = "_".join(tickers_selected) if len(tickers_selected) < 5 else "Multiple"
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
    """
    Displays the period selection UI, syncs it with session_state.
    Returns the fetch arguments (kwargs).
    """
    # Define default and selectable periods
    
    AVAILABLE_PERIODS = ["1mo", "3mo", "6mo", "ytd", "1y", "2y", "5y", "Custom Date"]
    
    # Initialize global default if not present
    if 'active_period' not in st.session_state:
        st.session_state['active_period'] = DEFAULT_LOOKBACK_PERIOD
    
    # Determine index for selectbox based on current session state
    current_selection = st.session_state['active_period']
    if current_selection not in AVAILABLE_PERIODS:
        current_selection = DEFAULT_LOOKBACK_PERIOD

    default_index = AVAILABLE_PERIODS.index(current_selection)

    with st.sidebar:
        st.header("📅 Configuration")
        
        # Widget: Writes to a temporary key
        selected_period = st.selectbox(
            "Lookback Period", 
            options=AVAILABLE_PERIODS, 
            index=default_index, 
            key='_period_select_widget' # Internal key for the widget
        )

        # Sync Widget -> Session State
        if selected_period != st.session_state['active_period']:
            st.session_state['active_period'] = selected_period

        # Initialize the dictionary to hold fetch arguments
        fetch_kwargs = {}
        
        if selected_period == "Custom Date":
            today = pd.Timestamp.now().normalize()
            default_start = today - pd.DateOffset(months=1)
            
            col1, col2 = st.columns(2)
            with col1:
                # Custom Start Date Selection
                start_date = st.date_input(
                    "Start Date", 
                    value=st.session_state.get('custom_start', default_start),
                    max_value=today,
                    key='custom_start_widget'
                )        
            with col2:
                # Custom End Date Selection (Default to Today)
                end_date = st.date_input(
                    "End Date", 
                    value=st.session_state.get('custom_end', today),
                    min_value=start_date, # End date cannot be before start date
                    max_value=today,
                    key='custom_end_widget'
                )

            # Save custom dates to Session State
            st.session_state['custom_start'] = start_date
            st.session_state['custom_end'] = end_date

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

    with st.sidebar.expander("ℹ️ Info", expanded=True):
        st.write("* Trading Interval:")
        st.write(f"**Fixed Interval:** {FIXED_INTERVAL}")
        st.write(f"**Trading Days:** {num_days}")        
        st.write(f"**First Price Date:** {first_date.strftime('%Y-%m-%d') if first_date else 'N/A'}")
        st.write(f"**Last Price Date:** {last_date.strftime('%Y-%m-%d') if last_date else 'N/A'}")
        st.write("* Parameters:")
        st.write(f"**Annualized Risk Free rate:** {RISK_FREE_RATE*100:.2f}%")       
        st.write(f"**Benckmark ticker:** {BENCHMARK_INDEX}")
        st.write(f"**Forecast Horizon (Monte Carlo):** {FORECAST_HORIZON} months")        

def display_guides_section():
    """
    Displays the informational sidebar section with guides on calculations and usage.
    """
    st.sidebar.markdown("---")  
    with st.sidebar.expander("ℹ️ Guides", expanded=False):        
        st.subheader("Data & Methodology")
        
        st.markdown(
            """
            **Data Source:** Market data and fundamentals are sourced via Yahoo Finance API to a local database.
            
            **Lookback Period:** All return and volatility metrics are calculated based on the specific period selected.
            """
        )

        st.markdown("---")
        st.subheader("Example Use Case: Value + Momentum")

        st.markdown("**1. Market Screening (Main Page)**")
        st.markdown("""
        1. **Select Period:** `1mo` to identify stocks with recent short-term momentum.
        2. **Filter #1:** `priceToBook` **Greater than** `0`.  
           *(Removes distressed companies with negative equity).*
        3. **Filter #2:** Add filter for `alpha` **Greater than** `10`.  
           *(Isolates stocks outperforming the benchmark).*
        4. **Select Candidates:** Sort table by `enToEbitda` (ascending) to find undervalued companies:
            * Select top rows with `enToEbitda` < `15`.
            * For rows with `None` (missing data), select if `priceToBook` < `2`.
            * ✅ Select `SPY` for reference.
        5. **Add to Watchlist:** Click the button below the table.
        """)
        
        st.markdown("---")
        st.markdown("**2. Selection (Watchlist Page)**")
        st.markdown("""
        6. **Select Period:** Switch to `2y` to view medium-term consistency.
        7. **Filter by Risk:** Sort by `sharpeRatio` (descending).
        8. **Refine:** Unfollow `SPY` and any ticker with a **lower Sharpe Ratio** than `SPY`.
        9. **Backtest:** Select the remaining "Winners" and click **Backtest Portfolio**.
        """)
        
        st.markdown("---")
        st.markdown("**3. Validation (Backtest Page)**")
        st.markdown("""
        10. **Select Period:** `5y` for long-term stress testing.
        11. **Analyze:** Check if the portfolio survives the `Max Drawdown` of major market crashes compared to the index.
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