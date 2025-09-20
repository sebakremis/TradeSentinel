# pages/02_Portfolio_Dashboard.py
import streamlit as st
import pandas as pd

# The code for the dashboard is now a standalone script
st.title("📈 Simulated Portfolio Analysis")
    
# Retrieve the data directly from session state
portfolio_tuples = st.session_state.get('portfolio', None)

if portfolio_tuples is None:
    st.warning("No portfolio data to display. Please simulate a portfolio from the main page.")
    # Use st.switch_page for proper navigation
    if st.button("Go back to Market View"):
        st.switch_page("main.py")
else:
    st.header("Portfolio Breakdown")
    
    portfolio_df = pd.DataFrame(portfolio_tuples, columns=['Ticker', 'Shares'])
    st.dataframe(portfolio_df, hide_index=True)

    # You can add more analysis here, like charts or other metrics
    st.bar_chart(portfolio_df.set_index('Ticker'))

    # Use st.switch_page for proper navigation
    if st.button("Go back to Market View"):
        st.switch_page("main.py")