# src/main.py
import streamlit as st
import tickers_store
import data_manager

st.set_page_config(page_title="TS Portfolio Analytics", layout="wide")
st.title("📊 TS Portfolio Analytics")

# Load tickers
tickers = tickers_store.load_followed_tickers()

st.subheader("Followed Tickers")
st.write(tickers)

# Fetch and display data
for ticker in tickers:
    st.markdown(f"### {ticker}")
    try:
        df = data_manager.load_ticker_data(ticker)
        st.dataframe(df.head())  # preview only
    except Exception as e:
        st.error(f"Failed to load {ticker}: {e}")


