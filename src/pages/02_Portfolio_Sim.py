# pages/02_Portfolio_Sim.py
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import datetime as dt

# Import database and logging tools
from src.database_manager import init_db, save_prices_to_db, load_prices_from_db
from src.indicators import calculate_price_change # reused function
from log_utils import info, warn, error
from metrics import (
    calculate_var, calculate_cvar, sharpe_ratio, sortino_ratio,
    calmar_ratio, max_drawdown, correlation_matrix, win_loss_stats
)


# --- Configuration and Initialization ---
DB_NAME = 'portfolio_data.db'
init_db(DB_NAME)

# --- Cached Data Fetchers ---

@st.cache_data(ttl=86400) # Cache sector data for 24 hours
def _get_sector(ticker: str) -> str:
    """Fetch sector for a ticker using yfinance, with caching."""
    try:
        yf_t = yf.Ticker(ticker)
        # Using yf_t.info is a simpler and more reliable approach
        info_dict = yf_t.info or {}
        sector = info_dict.get("sector", "Unknown")
    except Exception as e:
        warn(f"Could not fetch sector for {ticker}: {e}")
        sector = "Unknown"
    return sector

@st.cache_data(ttl=3600)
def _get_portfolio_data_cached(tickers: list, period: str, interval: str) -> dict:
    """
    Fetches historical data for portfolio tickers from the database first.
    If not available, fetches from yfinance, saves to DB, and returns data.
    """
    # Load data from the dedicated portfolio database
    db_data = load_prices_from_db(DB_NAME)

    # Check for the existence of Ticker and Date columns in the loaded data
    if "Ticker" not in db_data.columns or "Date" not in db_data.columns:
        warn("Database data is not in the expected format. Proceeding with yfinance fetch.")
        has_all_data_in_db = False
    else:
        # Correctly set the index to be a MultiIndex of Date and Ticker
        db_data['Date'] = pd.to_datetime(db_data['Date'])
        # Handle potential duplicates before setting index
        db_data = db_data.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
        db_data = db_data.set_index(['Ticker', 'Date']).sort_index()

        # Check if all required tickers are present in the database
        # This check is good, but doesn't check for required period/interval.
        # Given the current data load/save structure, clearing the cache on refresh
        # is the most robust way to ensure the *right* data is used.
        has_all_data_in_db = all(ticker in db_data.index.get_level_values('Ticker') for ticker in tickers)

    if has_all_data_in_db and not db_data.empty:
        info("Using cached data from database.")
        prices = {}
        for ticker in tickers:
            # Check if ticker data is present before attempting to loc
            if ticker in db_data.index.get_level_values('Ticker'):
                prices[ticker] = db_data.loc[ticker].copy()
            else:
                warn(f"Ticker {ticker} expected in DB but not found. Will fetch.")
                has_all_data_in_db = False # Force API fetch if any ticker is missing
                break
        if has_all_data_in_db:
            return prices

    info("Data not fully in database or cache cleared. Fetching from API...")
    try:
        raw_data = yf.download(
            tickers=tickers,
            period=period,
            interval=interval,
            group_by='ticker',
            auto_adjust=True,
            threads=True,
            progress=False
        )
    except Exception as e:
        st.error(f"Error fetching data from yfinance: {e}")
        return {}

    if raw_data.empty:
        st.warning("No data returned from yfinance.")
        return {}

    # Process and save to database
    all_data_for_db = []
    processed_prices = {}
    
    # Determine if the data has a MultiIndex (multiple tickers) or a regular index (single ticker)
    is_multi_ticker = isinstance(raw_data.columns, pd.MultiIndex)
    
    for ticker in tickers:
        # Add sector information here!
        sector = _get_sector(ticker)

        df = None
        if is_multi_ticker:
            if (ticker, 'Close') in raw_data.columns:
                df = raw_data[ticker].copy()
        else: # Single ticker case
            if 'Close' in raw_data.columns and len(tickers) == 1 and tickers[0] == ticker:
                df = raw_data.copy()

        if df is not None and 'Close' in df.columns:
            # Ensure index is datetime before manipulating dates
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            df['Ticker'] = ticker
            df['Sector'] = sector # Add sector column
            processed_prices[ticker] = df
            
            # For database storage, reset index and rename
            # Use ISO format string for robust date storage
            df_for_db = df.reset_index(names=['Date'])
            df_for_db['Date'] = df_for_db['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
            all_data_for_db.append(df_for_db)
        else:
            warn(f"No valid data found for {ticker}, skipping.")

    if all_data_for_db:
        combined_df = pd.concat(all_data_for_db, ignore_index=True)
        save_prices_to_db(combined_df, DB_NAME)
        # st.success("✅ New data fetched and saved to database.")

    return processed_prices

# --- Core Logic Functions (Refactored from the main script body) ---

def setup_sidebar_controls():
    """Sets up the sidebar controls for portfolio definition and parameters."""
    portfolio_tuples = st.session_state.get('portfolio', None)
    if portfolio_tuples:
        sim_portfolio = pd.DataFrame(portfolio_tuples, columns=['Ticker', 'Quantity'])
    else:
        sim_portfolio = pd.DataFrame(columns=['Ticker', 'Quantity'])

    st.sidebar.title("Set portfolio to analyze:")
    portfolio_df = st.sidebar.data_editor(sim_portfolio, num_rows="dynamic", width="stretch")

    # --- MODIFICATION START ---
    
    # Set the fixed interval
    FIXED_INTERVAL = "1d"
    
    # Set the limited period options
    PERIOD_OPTIONS = ["1mo", "3mo", "6mo", "1y", "ytd", "max"]
    
    # Period Selection (Use '1y' as the default index)
    period_input = st.sidebar.selectbox(
        "Lookback Period", 
        PERIOD_OPTIONS, 
        index=PERIOD_OPTIONS.index("1y"), 
        key="active_period_input"
    )

    # Display fixed interval, without a selectbox
    st.sidebar.markdown(f"**Interval:** `{FIXED_INTERVAL}` (Daily)")
    interval_input = FIXED_INTERVAL
    
    # --- MODIFICATION END ---
    
    refresh = st.sidebar.button("Refresh Data")
    
    # --- On refresh, validate and commit parameters ---
    if refresh:
        tickers_input = portfolio_df["Ticker"].dropna().astype(str).str.strip().tolist()
        quantities_input = portfolio_df["Quantity"]
        
        # Validation logic
        invalid_tickers = [t for t in tickers_input if not t or not t.replace('.', '').isalnum()]
        
        # Ensure quantities are numeric and non-negative (assuming a long-only or neutral position sim)
        quantities_clean = []
        invalid_quantities = []
        for q in quantities_input:
            # Allow NaN for empty rows, but will fillna(0) later
            if pd.isna(q):
                quantities_clean.append(0) 
            elif isinstance(q, (int, float)) and q >= 0:
                quantities_clean.append(int(q)) # Convert to int for quantities
            else:
                invalid_quantities.append(q)

        if invalid_tickers or invalid_quantities:
            st.sidebar.error("Invalid input. Check tickers (must be alphanumeric/dot) and quantities (must be non-negative numbers).")
            st.stop()
            
        # Commit to session state for the main content area
        st.session_state.active_tickers = tickers_input
        st.session_state.active_quantities = dict(zip(tickers_input, quantities_clean))
        st.session_state.active_period = period_input
        st.session_state.active_interval = interval_input
        
        # Clear cache to force a fresh data fetch from API/DB
        _get_portfolio_data_cached.clear()
        st.rerun()

def calculate_pnl_data(prices: dict, quantities: dict) -> pd.DataFrame:
    """Calculates PnL and position snapshot data per ticker."""
    pnl_data = []
    for ticker, df in prices.items():
        if df is not None and not df.empty:
            try:
                # Ensure start and end values are scalars
                start = df["Close"].iloc[0]
                end = df["Close"].iloc[-1]
                
                # Use .item() to safely extract scalar from numpy/pandas series if present
                if hasattr(start, "item"): start = start.item()
                if hasattr(end, "item"): end = end.item()

                qty = quantities.get(ticker, 0)
                weighted_pnl = (end - start) * qty
                position_value = end * qty
                pct = ((end - start) / start) * 100 if start != 0 else 0.0
                
                # Get sector from the DataFrame (added in _get_portfolio_data_cached)
                sector = df["Sector"].iloc[0] if "Sector" in df.columns else "Unknown"

                pnl_data.append({
                    "Ticker": ticker,
                    "Sector": sector, # Include Sector here for later use
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
        .hide(subset=["Sector"], axis=1), # Hide sector from this view
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

def prepare_pnl_time_series(prices: dict, quantities: dict) -> pd.DataFrame:
    """Processes raw price data into a combined DataFrame for time series charting."""
    pnl_time_data = []
    for ticker, df in prices.items():
        if df is not None and not df.empty:
            try:
                tmp = df.copy()

                # Ensure the index is a datetime object
                if not isinstance(tmp.index, pd.DatetimeIndex):
                    tmp.index = pd.to_datetime(tmp.index)
                
                qty = quantities.get(ticker, 0)
                tmp["Quantity"] = qty
                tmp["Price"] = tmp["Close"]
                tmp["Position Value ($)"] = tmp["Price"] * tmp["Quantity"]
                # PnL from the start of the selected period
                tmp["PnL"] = (tmp["Price"] - tmp["Price"].iloc[0]) * tmp["Quantity"]
                tmp["Ticker"] = ticker
                tmp["Time"] = tmp.index # 'Time' column is now guaranteed datetime
                
                pnl_time_data.append(
                    tmp[["Time", "Ticker", "Quantity", "Price", "Position Value ($)", "PnL"]]
                )
            except Exception as e:
                st.warning(f"{ticker}: Error building time series — {e}")

    return pd.concat(pnl_time_data, ignore_index=True) if pnl_time_data else pd.DataFrame()


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
            .interactive() # Add interactivity for zoom/pan
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No time series data available for charting.")


def display_sector_allocation(df_pnl: pd.DataFrame):
    """Displays the portfolio allocation by sector using a pie chart and table."""
    st.subheader("📊 Portfolio Allocation by Sector")
    
    # Aggregate by sector (df_pnl already contains 'Sector' and 'Position Value ($)')
    sector_alloc = (
        df_pnl.groupby("Sector")
        .agg({
            "Position Value ($)": "sum",
            "Ticker": lambda s: ", ".join(sorted(set(s)))
        })
        .reset_index()
        .rename(columns={"Position Value ($)": "PositionValue"}) # Rename for clarity
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
        
        # Display the simplified table below (Sector + Ticker, no index, formatted value)
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

    # Portfolio returns (daily or per interval)
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
        
    st.subheader("📈 Asset Correlation Matrix")

    # Pivot to get one column per asset
    price_wide = combined_df.pivot(index="Time", columns="Ticker", values="Price")

    # Compute correlation matrix and round
    corr_df = correlation_matrix(price_wide).round(4) # Rounding to 4 is cleaner for display

    # Display with conditional formatting
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
    
    date_min = combined_df["Time"].min().normalize().date() # Use normalize() to get pure date for min
    date_max = combined_df["Time"].max().normalize().date() # Use normalize() to get pure date for max
    
    date_range = st.date_input(
        "Select Date Range",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
    )
    
    # Ensure date_range has two elements before filtering
    if len(date_range) != 2:
        st.warning("Please select a valid date range.")
        return

    # Filter the DataFrame
    filtered_df = combined_df[
        combined_df["Ticker"].isin(tickers_selected)
        & (combined_df["Time"].dt.date >= date_range[0])
        & (combined_df["Time"].dt.date <= date_range[1])
    ].copy()
    
    if not filtered_df.empty:
        
        # Sort so most recent entries appear first
        df_display = filtered_df.sort_values("Time", ascending=False).copy()

        # Split into Date and Time columns
        df_display["Date"] = df_display["Time"].dt.strftime("%Y-%m-%d")
        df_display["Time"] = df_display["Time"].dt.strftime("%H:%M:%S")
        
        # Remove original datetime column
        df_display = df_display.drop(columns=["Time"], errors='ignore')

        # Reorder so Date/Ticker appear first
        cols_order = ["Date", "Ticker", "Quantity", "Price", "Position Value ($)", "PnL"]
        df_display = df_display[cols_order].reset_index(drop=True)
        
        # --- Round numeric columns to 2 decimals for export and display ---
        for col in ["Price", "Position Value ($)", "PnL"]:
            if col in df_display.columns:
                df_display[col] = df_display[col].astype(float).round(2)

        # --- Display with formatted view ---
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

# --- Main App Execution ---

def main():
    """The main function to run the Streamlit app content."""
    st.title("📈 Simulated Portfolio Analysis")
    
    # 1. Setup Sidebar and Control Flow
    setup_sidebar_controls()
    
    # Stop execution if parameters haven't been finalized by the Refresh button
    if "active_tickers" not in st.session_state:
        st.info("Set your portfolio parameters and click **Refresh Data** to load the dashboard.")
        st.stop()

    # Retrieve finalized parameters
    tickers = st.session_state.active_tickers
    quantities = st.session_state.active_quantities
    period = st.session_state.active_period
    interval = st.session_state.active_interval

    # 2. Load Data
    with st.spinner(f"Loading market data for {len(tickers)} tickers over {period} @ {interval}..."):
        prices = _get_portfolio_data_cached(tickers, period=period, interval=interval)
        st.session_state.data = prices # Save fetched data to session state
    
    if not prices:
        st.error("Could not load data for the selected portfolio. Please check tickers and try again.")
        st.stop()
        
    # 3. Calculate Core PnL Data
    df_pnl = calculate_pnl_data(prices, quantities)
    if df_pnl.empty:
        st.error("PnL calculation failed for all tickers.")
        st.stop()

    # --- Display Sections ---

    # Per-Ticker Snapshot
    display_per_ticker_pnl(df_pnl)
    st.markdown("---")

    # Portfolio Summary & Pie Chart
    display_portfolio_summary(df_pnl)
    st.markdown("---")

    # Time Series Data Preparation (used by PnL Over Time and Advanced Metrics)
    combined_df = prepare_pnl_time_series(prices, quantities)

    # Portfolio PnL Over Time
    display_pnl_over_time(combined_df)
    st.markdown("---")

    # Sector Allocation
    display_sector_allocation(df_pnl)
    st.markdown("---")

    # Advanced Metrics
    display_advanced_metrics(combined_df)
    st.markdown("---")

    # Export Table
    display_export_table(combined_df)

    # Credits and Navigation
    st.markdown("---")
    st.markdown(
        "🔗 [View Source Code on GitHub](https://github.com/sebakremis/TradeSentinel)",
        unsafe_allow_html=True
    )
    st.caption("Built using Streamlit and Python.")
    # Use st.switch_page for proper navigation
    if st.button("Go back to Main Dashboard"):
        st.switch_page("main.py")

if __name__ == "__main__":
    main()