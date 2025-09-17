# src/main.py
import streamlit as st
import tickers_store

st.set_page_config(page_title="TS Portfolio Analytics", layout="wide")

st.title("📊 TS Portfolio Analytics")

# Load current tickers
tickers = tickers_store.load_followed_tickers()

st.sidebar.header("Manage Followed Tickers")

# Add new ticker
new_ticker = st.sidebar.text_input("Add Ticker")
if st.sidebar.button("Add"):
    if new_ticker:
        tickers_store.add_ticker(new_ticker.upper())
        st.sidebar.success(f"Added {new_ticker.upper()}")

# Remove ticker
ticker_to_remove = st.sidebar.selectbox("Remove Ticker", [""] + tickers)
if st.sidebar.button("Remove") and ticker_to_remove:
    tickers_store.remove_ticker(ticker_to_remove)
    st.sidebar.warning(f"Removed {ticker_to_remove}")

# Display followed tickers
st.subheader("Currently Followed Tickers")
st.write(tickers_store.load_followed_tickers())

