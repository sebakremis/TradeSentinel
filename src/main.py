# src/main.py
import streamlit as st
import tickers_store
import data_manager

st.set_page_config(page_title="TS Portfolio Analytics", layout="wide")
st.title("📊 TS Portfolio Analytics")

# --- Sidebar: Manage Followed Tickers ---
st.sidebar.header("Manage Followed Tickers")

# Load current tickers
tickers = tickers_store.load_followed_tickers()

# Add new ticker
new_ticker = st.sidebar.text_input("Add Ticker")
if st.sidebar.button("Add"):
    if new_ticker:
        tickers_store.add_ticker(new_ticker.upper())
        st.sidebar.success(f"Added {new_ticker.upper()}")
        st.rerun()   # <-- use this instead of experimental_rerun

# Remove ticker
if tickers:
    ticker_to_remove = st.sidebar.selectbox("Remove Ticker", [""] + tickers)
    if st.sidebar.button("Remove") and ticker_to_remove:
        tickers_store.remove_ticker(ticker_to_remove)
        st.sidebar.warning(f"Removed {ticker_to_remove}")
        st.rerun()


# --- Main content ---
st.subheader("Currently Followed Tickers")
tickers = tickers_store.load_followed_tickers()
st.write(tickers)

# Fetch and display data for each ticker
for ticker in tickers:
    st.markdown(f"### {ticker}")
    try:
        df = data_manager.load_ticker_data(ticker)
        st.dataframe(df.head())
    except Exception as e:
        st.error(f"Failed to load {ticker}: {e}")



