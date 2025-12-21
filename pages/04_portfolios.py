import streamlit as st
import pandas as pd
import json
import time

from src.config import PORTFOLIO_FILE
from src.dashboard_manager import get_stock_data
from src.dashboard_display import (
    display_per_ticker_pnl, display_portfolio_summary,
    display_pnl_over_time, display_sector_allocation,
    display_advanced_metrics, display_export_table, display_credits,
    display_guides_section
)

st.set_page_config(page_title="💼 Portfolio Tracker", layout="wide")

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

# --- Logic: Handle Staggered Dates ---

def process_portfolio_history(prices_dict, portfolio_config):
    """
    Combines price data with purchase dates to create a realistic timeline.
    For each ticker, value is 0 before its specific Purchase Date.
    """
    # Create a mapping of Ticker -> {Qty, PurchaseDate, PurchasePrice}
    config_map = {item['Ticker']: item for item in portfolio_config}
    
    adjusted_series = {}
    
    for ticker, df in prices_dict.items():
        if ticker not in config_map or df.empty:
            continue
            
        purchase_date = pd.to_datetime(config_map[ticker]['Purchase Date']).normalize()
        qty = config_map[ticker]['Quantity']
        
        # Create a series of the asset's value over time
        # Logic: If CurrentDate < PurchaseDate, Value = 0. Else Value = Price * Qty
        
        # Reindex to ensure we cover the whole range if needed, or just work with available dates
        series = df['close'] * qty
        
        # --- FIX: Ensure the index is Timezone Naive ---
        # If the market data has a timezone, strip it so it matches the simple 'purchase_date'
        if series.index.tz is not None:
            series.index = series.index.tz_localize(None)
            
        # Mask dates before purchase (Set value to 0 before we owned it)
        mask_before_purchase = series.index < purchase_date
        series.loc[mask_before_purchase] = 0
        
        adjusted_series[ticker] = series

    # Combine into a single DataFrame (Total Portfolio Value over time)
    # Handle case where adjusted_series might be empty to avoid concat errors
    if not adjusted_series:
        return pd.DataFrame(columns=['Total Portfolio Value'])

    portfolio_value_df = pd.DataFrame(adjusted_series)
    portfolio_value_df['Total Portfolio Value'] = portfolio_value_df.sum(axis=1)
    
    return portfolio_value_df

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
    
    # --- FIX: HANDLE REDIRECT FROM SAVE ---
    # This must happen BEFORE the widgets are instantiated
    if 'newly_saved_portfolio' in st.session_state:
        # 1. Force the Radio button to 'View Existing'
        st.session_state['portfolio_mode_radio'] = "View Existing"
        # 2. Force the Selectbox to the new name
        st.session_state['portfolio_select_box'] = st.session_state['newly_saved_portfolio']
        # 3. Clean up the flag
        del st.session_state['newly_saved_portfolio']

    # Initialize edit mode state
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

    # Guides on sidebar
    display_guides_section()

    return mode, selected_portfolio_name, portfolio_data

def render_editor(current_data=None, current_name=None):
    st.subheader(f"🛠️ {'Edit Portfolio' if current_name else 'Create New Portfolio'}")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        # Pre-fill name if editing
        default_name = current_name if current_name else ""
        new_name = st.text_input("Portfolio Name", value=default_name, placeholder="e.g., Tech Growth Fund")
    
    # Define Schema for the Editor
    if current_data:
        # Load existing into DF
        df = pd.DataFrame(current_data)
        # Ensure correct types for editor
        df['Purchase Date'] = pd.to_datetime(df['Purchase Date']).dt.date
    else:
        # Empty template
        df = pd.DataFrame({
            "Ticker": pd.Series(dtype="str"),
            "Quantity": pd.Series(dtype="int"),
            "Purchase Date": pd.Series(dtype="object"), 
            "Purchase Price": pd.Series(dtype="float"),
        })

    # The dynamic editor allows adding new rows (tickers) and editing existing ones
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

            # Clean Data
            clean_df = edited_df.dropna(how='any')
            if clean_df.empty:
                st.error("Portfolio cannot be empty.")
                return
                
            # Convert dates to string for JSON serialization
            clean_df['Purchase Date'] = clean_df['Purchase Date'].astype(str)
            clean_df['Ticker'] = clean_df['Ticker'].str.upper().str.strip()
            
            # Save
            with st.spinner("Saving..."):
                data_to_save = clean_df.to_dict(orient='records')
                save_portfolio(new_name, data_to_save)
                
                if current_name and new_name != current_name:
                    delete_portfolio(current_name)

                # Redirect flag
                st.session_state['newly_saved_portfolio'] = new_name
                
                # Turn off edit mode
                st.session_state['edit_mode'] = False
                
                st.session_state['success_msg'] = f"Portfolio '{new_name}' saved successfully!"
                time.sleep(0.5) 
            
            st.rerun()

    with col_cancel:
        # Cancel Button to exit edit mode
        if st.button("Cancel"):
            st.session_state['edit_mode'] = False
            st.rerun()

def prepare_detailed_export(prices_dict, portfolio_config):
    """
    Creates a detailed long-format DataFrame for the export table.
    Columns: Time, Ticker, Quantity, Price, Position Value ($)
    """
    all_dfs = []
    config_map = {item['Ticker']: item for item in portfolio_config}

    for ticker, df in prices_dict.items():
        if ticker not in config_map or df.empty:
            continue
            
        qty = config_map[ticker]['Quantity']
        # Purchase Price needed if you want to calculate historical PnL, 
        # but for now we just show Market Value history.
        
        pur_date = pd.to_datetime(config_map[ticker]['Purchase Date']).normalize()
        
        # Get Price Series
        series_price = df['close'].copy()
        
        # --- Timezone Fix (Same as before) ---
        if series_price.index.tz is not None:
            series_price.index = series_price.index.tz_localize(None)
            
        # Filter: Only include dates AFTER purchase
        series_price = series_price[series_price.index >= pur_date]
        
        if series_price.empty:
            continue

        # Create DataFrame
        temp_df = series_price.to_frame(name='Price')
        temp_df['Time'] = temp_df.index
        temp_df['Ticker'] = ticker
        temp_df['Quantity'] = qty
        temp_df['Position Value ($)'] = temp_df['Price'] * qty
        
        # Optional: Calculate Daily PnL vs Cost Basis if you wanted, 
        # but simplistic Value is enough to fix the error.
        
        all_dfs.append(temp_df)

    if not all_dfs:
        return pd.DataFrame(columns=['Time', 'Ticker', 'Price', 'Quantity', 'Position Value ($)'])
        
    return pd.concat(all_dfs, ignore_index=True)

def main():
    st.title("💼 Portfolio Tracker")
    
    mode, name, data = render_sidebar()

    # --- Router Logic ---

    # 1. Check for Edit Mode Override
    if st.session_state.get('edit_mode') and name and data:
        # We pass both data AND the name so the editor knows what we are editing
        render_editor(current_data=data, current_name=name)
        return

    # 2. Standard Create Mode
    if mode == "Create":
        render_editor()
        return

    # 3. View / Analyze Mode
    if not name or not data:
        st.info("Select a portfolio from the sidebar to view analysis.")
        st.stop()
    
    st.markdown(f"### Analyzing: **{name}**")
    
    # 1. Prepare Data for Fetching
    # We need to fetch data starting from the earliest purchase date in the portfolio
    df_config = pd.DataFrame(data)
    earliest_date = pd.to_datetime(df_config['Purchase Date']).min()
    tickers = df_config['Ticker'].tolist()
    
    # Calculate totals for summary metrics
    # Logic: Current Value requires fetching live price. 
    # Logic: Cost Basis = Qty * Purchase Price
    df_config['Cost Basis'] = df_config['Quantity'] * df_config['Purchase Price']
    total_invested = df_config['Cost Basis'].sum()

    # 2. Fetch Market Data
    with st.spinner(f"Fetching data from {earliest_date.date()}..."):
        # Fetch data with a small buffer before the earliest date
        prices_df = get_stock_data(tickers, start=earliest_date, interval='1d')
        
        if prices_df.empty:
            st.error("Could not fetch market data. Check your tickers.")
            st.stop()
            
        prices_df.set_index('Date', inplace=True)

        # Force sort descending
        prices_df.sort_index(ascending=True, inplace=True)

        # Split into dict of dataframes
        prices_dict = dict(tuple(prices_df.groupby('Ticker')))

    # 3. Process Data (Handle Staggered Entry)
    # This DF has the daily value of the portfolio accounting for when assets were bought
    time_series_df = process_portfolio_history(prices_dict, data)

    # 4. Calculate PnL Snapshot (Current State)
    
    current_pnl_rows = []
    
    for item in data:
        ticker = item['Ticker']
        qty = item['Quantity']
        avg_cost = item['Purchase Price']
        
        if ticker in prices_dict:
            df_ticker = prices_dict[ticker]
            
            # 1. Get Price Data
            # Use iloc to get the last available row
            current_price = df_ticker['close'].iloc[-1]
            prev_price = df_ticker['close'].iloc[-2] if len(df_ticker) > 1 else current_price
            
            # 2. Get Sector Data (DIRECTLY FROM DB)
            # The 'get_stock_data' function already merged metadata columns.
            # We check for 'sector' or 'Sector' to be safe with CSV casing.
            sector = 'Unknown'
            if 'sector' in df_ticker.columns:
                sector = df_ticker['sector'].iloc[0]
            elif 'Sector' in df_ticker.columns:
                sector = df_ticker['Sector'].iloc[0]
                
            # Handle empty/NaN values from the CSV
            if pd.isna(sector) or sector == '':
                sector = 'Other'

            # 3. Calculate Metrics
            market_value = current_price * qty
            cost_basis = avg_cost * qty
            total_return = market_value - cost_basis
            total_return_pct = (total_return / cost_basis) if cost_basis > 0 else 0
            daily_change_pct = (current_price - prev_price) / prev_price
            
            current_pnl_rows.append({
                'Ticker': ticker,
                'sector': sector,
                'Quantity': qty,
                'Current Price': current_price,
                'Avg Cost': avg_cost,
                'Position Value ($)': market_value,
                'Daily Change %': daily_change_pct,
                'Total Return': total_return,
                'Total Return %': total_return_pct
            })
            
    df_snapshot = pd.DataFrame(current_pnl_rows)

    # --- Dashboard Display ---
    
    # Top Level Metrics
    current_total_value = df_snapshot['Position Value ($)'].sum()
    total_pnl = current_total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested) if total_invested > 0 else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Portfolio Value", f"${current_total_value:,.2f}")
    c2.metric("Total Invested Cost", f"${total_invested:,.2f}")
    c3.metric("Unrealized PnL", f"${total_pnl:,.2f}", f"{total_pnl_pct:.2%}")
    
    st.markdown("---")
    
    # Reuse your existing display components where possible
    # We map our custom df_snapshot to what display_per_ticker_pnl likely expects
    # If the column names differ in your src, you might need to adjust the names below
    st.subheader("Performance by Asset")
    st.dataframe(
        df_snapshot.style.format({
            'Current Price': "${:.2f}",
            'Avg Cost': "${:.2f}",
            'Market Value': "${:,.2f}",
            'Daily Change %': "{:.2%}",
            'Total Return': "${:,.2f}",
            'Total Return %': "{:.2%}"
        }),
        width='stretch'
    )
    
    st.markdown("---")
    
    # Portfolio Composition
    display_sector_allocation(df_snapshot) # Assuming this takes a DF with 'Ticker' and 'Market Value' or 'Quantity'
    
    st.markdown("---")
    
    # Historical Chart
    # We pass the specially prepared time_series_df
    st.subheader("Portfolio Value Over Time")
    st.line_chart(time_series_df['Total Portfolio Value'])
    
    st.markdown("---")
    
    # Generate detailed data for the export table ---
    export_df = prepare_detailed_export(prices_dict, data)
    display_export_table(export_df)
    
    display_credits()

if __name__ == "__main__":
    main()