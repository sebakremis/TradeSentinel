import streamlit as st
import pandas as pd
import json
import time

from src.config import PORTFOLIO_FILE
from src.dashboard_manager import get_stock_data
from src.analytics import calculate_pnl_data, prepare_pnl_time_series
from src.dashboard_display import (
    display_per_ticker_pnl, display_portfolio_summary,
    display_pnl_over_time, display_sector_allocation,
    display_export_table, display_credits,
    display_guides_section
)

st.set_page_config(page_title="💼 Portfolio Tracker", layout="wide")

# --- Portfolio Management Functions (Unchanged) ---

def load_portfolios():
    """Loads portfolios from local JSON file."""
    if not PORTFOLIO_FILE:
        return {}
    try:
        with open(PORTFOLIO_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_portfolio(name, data):
    """Saves a single portfolio to the JSON store."""
    portfolios = load_portfolios()
    portfolios[name] = data
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(portfolios, f, indent=4, default=str)

def delete_portfolio(name):
    """Deletes a portfolio."""
    portfolios = load_portfolios()
    if name in portfolios:
        del portfolios[name]
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(portfolios, f, indent=4)

# --- UI Sections ---

@st.dialog("Confirm Deletion")
def confirmation_dialog(portfolio_name):
    st.write(f"Are you sure you want to delete **{portfolio_name}**?")
    st.warning("This action cannot be undone.")
    
    col1, col2 = st.columns(2)
    if col1.button("Yes, Delete", type="primary"):
        delete_portfolio(portfolio_name)
        st.session_state['success_msg'] = "Portfolio deleted."
        st.rerun()
        
    if col2.button("Cancel"):
        st.rerun()

def render_sidebar():
    st.sidebar.title("Manage Portfolios")
    
    # Handle Redirect from Save
    if 'newly_saved_portfolio' in st.session_state:
        st.session_state['portfolio_mode_radio'] = "View Existing"
        st.session_state['portfolio_select_box'] = st.session_state['newly_saved_portfolio']
        del st.session_state['newly_saved_portfolio']

    if 'edit_mode' not in st.session_state:
        st.session_state['edit_mode'] = False
    
    mode = st.sidebar.radio(
        "Mode", 
        ["View Existing", "Create"], 
        label_visibility="collapsed",
        key="portfolio_mode_radio"
    )
    
    if mode == "Create" and st.session_state['edit_mode']:
        st.session_state['edit_mode'] = False
    
    saved_portfolios = load_portfolios()
    selected_portfolio_name = None
    portfolio_data = []

    if mode == "View Existing":
        if not saved_portfolios:
            st.sidebar.warning("No portfolios saved yet. Switch to 'Create' to start.")
        else:
            selected_portfolio_name = st.sidebar.selectbox(
                "Select Portfolio", 
                list(saved_portfolios.keys()),
                key="portfolio_select_box"
            )
            
            if selected_portfolio_name:
                portfolio_data = saved_portfolios[selected_portfolio_name]

                col1, col2 = st.sidebar.columns(2)                
                with col1:
                    if st.button("Edit Portfolio"):
                        st.session_state['edit_mode'] = True
                        st.rerun()
                        
                with col2:
                    if st.button("Delete Portfolio", type="primary"):
                        confirmation_dialog(selected_portfolio_name)

    display_guides_section()
    return mode, selected_portfolio_name, portfolio_data

def render_editor(current_data=None, current_name=None):
    st.subheader(f"🛠️ {'Edit Portfolio' if current_name else 'Create New Portfolio'}")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        default_name = current_name if current_name else ""
        new_name = st.text_input("Portfolio Name", value=default_name, placeholder="e.g., Tech Growth Fund")
    
    if current_data:
        df = pd.DataFrame(current_data)
        df['Purchase Date'] = pd.to_datetime(df['Purchase Date']).dt.date
    else:
        df = pd.DataFrame({
            "Ticker": pd.Series(dtype="str"),
            "Quantity": pd.Series(dtype="int"),
            "Purchase Date": pd.Series(dtype="object"), 
            "Purchase Price": pd.Series(dtype="float"),
        })

    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        width='stretch',
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", required=True, validate="^[A-Za-z0-9.]+$"),
            "Quantity": st.column_config.NumberColumn("Quantity", min_value=1, step=1, required=True),
            "Purchase Date": st.column_config.DateColumn("Purchase Date", required=True),
            "Purchase Price": st.column_config.NumberColumn("Unit Cost ($)", min_value=0.01, format="$%.2f", required=True)
        }
    )

    col_save, col_cancel = st.columns([1, 10])
    
    with col_save:
        if st.button("Save Portfolio", type="primary"):
            if not new_name:
                st.error("Please enter a portfolio name.")
                return

            clean_df = edited_df.dropna(how='any')
            if clean_df.empty:
                st.error("Portfolio cannot be empty.")
                return
                
            clean_df['Purchase Date'] = clean_df['Purchase Date'].astype(str)
            clean_df['Ticker'] = clean_df['Ticker'].str.upper().str.strip()
            
            with st.spinner("Saving..."):
                data_to_save = clean_df.to_dict(orient='records')
                save_portfolio(new_name, data_to_save)
                
                if current_name and new_name != current_name:
                    delete_portfolio(current_name)

                st.session_state['newly_saved_portfolio'] = new_name
                st.session_state['edit_mode'] = False
                st.session_state['success_msg'] = f"Portfolio '{new_name}' saved successfully!"
                time.sleep(0.5) 
            
            st.rerun()

    with col_cancel:
        if st.button("Cancel"):
            st.session_state['edit_mode'] = False
            st.rerun()

# --- Main App Execution ---

def main():
    st.title("💼 Portfolio Tracker")
    
    mode, name, data = render_sidebar()

    # Router Logic
    if st.session_state.get('edit_mode') and name and data:
        render_editor(current_data=data, current_name=name)
        return

    if mode == "Create":
        render_editor()
        return

    if not name or not data:
        st.info("Select a portfolio from the sidebar to view analysis.")
        st.stop()
    
    st.markdown(f"### Analyzing: **{name}**")
    
    # 1. Prepare Configuration
    # We load the config into dictionaries for fast lookup
    df_config = pd.DataFrame(data)
    
    # Map Ticker -> Quantity, Purchase Price, Purchase Date
    quantities = dict(zip(df_config['Ticker'], df_config['Quantity']))
    purchase_prices = dict(zip(df_config['Ticker'], df_config['Purchase Price']))
    purchase_dates = dict(zip(df_config['Ticker'], pd.to_datetime(df_config['Purchase Date']).dt.normalize()))
    
    earliest_date = df_config['Purchase Date'].min()
    tickers = df_config['Ticker'].tolist()
    
    # 2. Fetch Market Data
    # Fetch from the earliest purchase date in the entire portfolio
    with st.spinner(f"Fetching data from {earliest_date}..."):
        prices_df = get_stock_data(tickers, start=earliest_date, interval='1d')
        
        if prices_df.empty:
            st.error("Could not fetch market data. Check your tickers.")
            st.stop()
            
        prices_df.set_index('Date', inplace=True)
        prices_df.sort_index(ascending=True, inplace=True)
        
        # Group into dictionary
        prices_dict = dict(tuple(prices_df.groupby('Ticker')))

    # 3. Slice Data for Ownership Period
    # We only want to calculate Dividends and Time Series for the period we actually OWNED the stock.
    owned_prices = {}
    for ticker, df in prices_dict.items():
        if ticker in purchase_dates:
            p_date = purchase_dates[ticker]
            
            # timezone handling
            if df.index.tz is not None:
                df = df.copy()
                df.index = df.index.tz_localize(None)
            
            # Slice: Keep only rows >= Purchase Date
            owned_prices[ticker] = df[df.index >= p_date]

    # 4. Calculate PnL using Shared Function (Page 03 Logic)
    # This automatically handles Dividend Summation
    df_pnl = calculate_pnl_data(owned_prices, quantities)

    # 5. [CRITICAL] Override with Manual Cost Basis
    # The default calculate_pnl_data uses the "price at start of data" as the cost basis.
    # We must overwrite this with the user's manual "Purchase Price" from the JSON.
    if not df_pnl.empty:
        for index, row in df_pnl.iterrows():
            ticker = row['Ticker']
            if ticker in purchase_prices:
                manual_cost = purchase_prices[ticker]
                qty = row['Quantity']
                current_price = row['End Price']
                
                # Overwrite Start Price with Manual Purchase Price
                df_pnl.at[index, 'Start Price'] = manual_cost
                
                # Recalculate Price PnL (Capital Gains)
                price_pnl = (current_price - manual_cost) * qty
                df_pnl.at[index, 'PnL ($)'] = price_pnl
                
                # Recalculate Total Return (Capital Gains + Dividends)
                # Dividends ($) is already correct because we sliced the dataframe!
                total_return = price_pnl + row['Dividends ($)']
                df_pnl.at[index, 'Total Return ($)'] = total_return
                
                # Recalculate % Change
                if manual_cost > 0:
                    pct_change = ((current_price - manual_cost) / manual_cost) * 100
                else:
                    pct_change = 0.0
                df_pnl.at[index, 'Change (%)'] = pct_change

    # --- Dashboard Display ---
    # Now we can simply reuse the shared display functions!

    # A. Top Level Summary
    display_portfolio_summary(df_pnl)
    st.markdown("---")
    
    # B. Detailed Table
    display_per_ticker_pnl(df_pnl)
    st.markdown("---")
    
    # C. Time Series Chart
    # prepare_pnl_time_series handles generating the daily values.
    # Because we passed 'owned_prices', the chart will naturally start at the purchase date.
    combined_df = prepare_pnl_time_series(owned_prices, quantities)
    display_pnl_over_time(combined_df)
    st.markdown("---")
    
    # D. Sector Allocation
    display_sector_allocation(df_pnl)
    st.markdown("---")
    
    # E. Export Table
    display_export_table(combined_df)
    
    display_credits()

if __name__ == "__main__":
    main()