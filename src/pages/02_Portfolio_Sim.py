# pages/02_Portfolio_Sim.py
import streamlit as st
import pandas as pd

# Retrieve the data directly from session state
portfolio_tuples = st.session_state.get('portfolio', None)

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

    st.header("Portfolio Breakdown")
    
    portfolio_df = pd.DataFrame(portfolio_tuples, columns=['Ticker', 'Quantity'])
    st.dataframe(portfolio_df, hide_index=True)

    # You can add more analysis here, like charts or other metrics
    st.bar_chart(portfolio_df.set_index('Ticker'))

    # Use st.switch_page for proper navigation
    if st.button("Go back to Market View"):
        st.switch_page("main.py")