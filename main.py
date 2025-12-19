import streamlit as st
st.set_page_config(page_title="📊 tradeSentinel", layout="wide")
import pandas as pd
import numpy as np
import altair as alt
import datetime 
from src.dashboard_manager import calculate_all_indicators, get_stock_data
from src.tickers_manager import load_tickers, confirm_follow_dialog, TickerValidationError
from src.dashboard_display import highlight_change, display_credits, render_info_section
from src.indicators import annualized_risk_free_rate
from src.config import DATA_DIR, all_tickers_file

# ----------------------------------------------------------------------
# --- Data Helper Functions ---
# ----------------------------------------------------------------------

DISPLAY_COLUMNS = ['Ticker', 'sector', 'marketCap', 'beta', 'close', '52WeekHigh', 'enterpriseToEbitda', 'priceToBook',  'dividendYield', 'returnOnAssets', 'avgReturn', 'annualizedVol', 'sharpeRatio']

def _format_final_df(final_df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies rounding and ensures selected columns are present for display.
    """
    df = final_df.copy()

    # Ensure all DISPLAY_COLUMNS are present, filling missing with NaN
    for col in DISPLAY_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    
    # Convert marketCap to billions and round   
    if "marketCap" in df.columns:
        df["marketCap"] = (df["marketCap"] / 1_000_000_000).round(2)  # 2 decimal places
    
    # Convert returnOnAssets to percentage
    if "returnOnAssets" in df.columns:
        df["returnOnAssets"] = (df["returnOnAssets"] * 100).round(2)  
        
    # Select only the display columns
    df = df[DISPLAY_COLUMNS]

    # Apply rounding
    for col in ['close', 'startPrice', 'divPayout', 'avgReturn', 'annualizedVol', 'sharpeRatio']:
        if col in df.columns:
            df[col] = df[col].round(2)           
    return df

def _load_and_process_data(PeriodOrStart= "1y") -> (pd.DataFrame, pd.DataFrame, list): 
    # Load the DF for all tickers
    tickers_df = load_tickers(all_tickers_file)
    all_tickers = tickers_df['Ticker'].tolist() if not tickers_df.empty else []

    fetch_kwargs = {}

    if '|' in PeriodOrStart:
        start_date, end_date = PeriodOrStart.split('|')
        fetch_kwargs['start'] = start_date
        fetch_kwargs['end'] = end_date
        fetch_kwargs['period'] = None
    elif len(PeriodOrStart) > 5 and '-' in PeriodOrStart:
        fetch_kwargs['start'] = PeriodOrStart
        fetch_kwargs['period'] = None
    else:
        fetch_kwargs['period'] = PeriodOrStart
        fetch_kwargs['start'] = None
    
    # load prices and metadata for all tickers
    df_daily = get_stock_data(
        all_tickers,
        interval="1d",
        **fetch_kwargs
    )

    if df_daily.empty:
        return pd.DataFrame(), pd.DataFrame(), all_tickers

    df_daily = calculate_all_indicators(df_daily)

    final_df_unformatted = df_daily.groupby('Ticker').tail(1).copy()

    start_prices = df_daily.groupby('Ticker')['close'].first().reset_index()
    start_prices.rename(columns={'close': 'startPrice'}, inplace=True)
    final_df_unformatted = final_df_unformatted.merge(start_prices, on='Ticker', how='left')




    final_df = _format_final_df(final_df_unformatted)

    return final_df, df_daily, all_tickers 

# ----------------------------------------------------------------------
# --- UI Rendering Functions ---
# ----------------------------------------------------------------------

def _render_summary_table_and_portfolio(final_df: pd.DataFrame, df_daily: pd.DataFrame):
    """Renders the summary table and portfolio simulation controls."""
    st.subheader("Summary")
   
    if final_df.empty:
        st.info("No data available to display in the summary table.")
        return

    sorted_df = final_df.sort_values(by='sharpeRatio', ascending=False)

    # --- Apply Conditional Formatting using Pandas Styler ---
    display_df_styled = sorted_df.copy()
    display_df_styled['Select'] = False # This must be done on the DataFrame copy before styling
    
    # Apply the color function to the 'avgReturn' column
    styled_table = display_df_styled.style.map(
        highlight_change, 
        subset=['avgReturn'] 
    )

    # --- Render Data Editor ---
    edited_df = st.data_editor(
        styled_table,
        hide_index=True,
        width='stretch',
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "sector": st.column_config.TextColumn("sector"),
            "marketCap": st.column_config.NumberColumn("marketCap", format="$%.1f B", width="small"),
            "beta": st.column_config.NumberColumn("beta", format="%.2f", width="small"),
            "close": st.column_config.NumberColumn("close", help="Last price of the lookback period", format="$%.2f", width="small"),
            "52WeekHigh": st.column_config.NumberColumn("52wHigh", help="52 Week High price", format="$%.2f", width="small"),
            "priceToBook": st.column_config.NumberColumn("priceToBook", help="Price to Book ratio", format="%.2f", width="small"),
            "enterpriseToEbitda": st.column_config.NumberColumn("enToEbitda", help="Enterprise value to EBITDA ratio", format="%.2f", width="small"),
            "dividendYield": st.column_config.NumberColumn("divYield", help="dividend yeld", format="%.2f%%",width="small"),
            "returnOnAssets": st.column_config.NumberColumn("ROA%", help="Return on Assets", format="%.2f%%",width="small"),                       
            "avgReturn": st.column_config.NumberColumn("AAR%", help="Annualized Average return", format="%.2f%%", width="small"),
            "annualizedVol": st.column_config.NumberColumn("Vol%", help="Annualized Average volatility", format="%.2f%%", width="small"),
            "sharpeRatio": st.column_config.NumberColumn("sharpe", format="%.2f%%", width="small"),                      
            "Select": st.column_config.CheckboxColumn("select", default=False, width="small")
        },
        num_rows="fixed"
    )
    
    selected_tickers_df = edited_df[edited_df['Select']]
    selected_tickers = selected_tickers_df['Ticker'].tolist()

    # Market Screen buttons
    col1, col2 = st.columns([3, 1])
    with col1:
        pass
    with col2:
        if st.button("Follow Selected Tickers", disabled=not selected_tickers):
            confirm_follow_dialog(selected_tickers)

# ----------------------------------------------------------------------
# --- Main Dashboard Function ---
# ----------------------------------------------------------------------

def main():
    st.set_page_config(layout="wide")
    st.title("📊 tradeSentinel")
    # Guide section in sidebar
    render_info_section()

    #--- User Input for Data Period ---
        
    # Define selectable periods
    AVAILABLE_PERIODS = ["3mo", "6mo", "ytd", "1y", "2y", "5y", "Custom Date"]
    
    # 1. Period Selection
    selected_period = st.selectbox(
        "Lookback Period", 
        options=AVAILABLE_PERIODS, 
        index=AVAILABLE_PERIODS.index("1y"), # Default to 1 year
        key='data_period_select'
    )
    
    # Initialize the argument to be passed to the data fetcher
    period_arg = selected_period
    
    if selected_period == "Custom Date":
        
        # Define default values
        today = pd.Timestamp.now().normalize()
        default_start_date = today - pd.DateOffset(years=1)
        
        col1, col2 = st.columns(2)

        with col1:
            # 2a. Custom Start Date Selection
            custom_start_date = st.date_input(
                "Select Analysis **Start Date**", 
                value=default_start_date,
                max_value=today,
                key='custom_start_date_select'
            )
        
        with col2:
            # 2b. Custom End Date Selection (Default to Today)
            custom_end_date = st.date_input(
                "Select Analysis **End Date**", 
                value=today,
                min_value=custom_start_date, # End date cannot be before start date
                max_value=today,
                key='custom_end_date_select'
            )

        # Pack both dates into a tuple or list string to pass as the argument
        period_arg = f"{custom_start_date}|{custom_end_date}" 

    st.markdown("---") # Separator for cleaner UI
    
    # Load and process all data required for the main display
    # Pass the custom period/date argument
    final_df, df_daily, all_tickers = _load_and_process_data(PeriodOrStart=period_arg)
  
    # Save the period_arg into the session state
    st.session_state['main_dashboard_period_arg'] = period_arg 

    # Info section
    if not df_daily.empty and 'Date' in df_daily.columns:
        num_days = df_daily['Date'].nunique()
        first_date = pd.to_datetime(df_daily['Date'].min())
        last_date = pd.to_datetime(df_daily['Date'].max())
    else:
        num_days = 0
        first_date, last_date = None, None

    with st.expander("ℹ️ Trading Period Info", expanded=False):
        st.write(f"**Trading Days:** {num_days}")
        st.write(f"**First Price Date:** {first_date.strftime('%Y-%m-%d') if first_date else 'N/A'}")
        st.write(f"**Last Price Date:** {last_date.strftime('%Y-%m-%d') if last_date else 'N/A'}")
        st.write(f"**Annualized Risk Free rate:** {annualized_risk_free_rate*100:.2f}% (assumed risk-free rate for Sharpe Ratio calculation)")

    if not final_df.empty:
        # Render the display sections if data is present
        _render_summary_table_and_portfolio(final_df, df_daily) # Pass df_daily to the summary table function
    else:
        st.info("No data found.")
        
    # Credits
    display_credits()    

if __name__ == "__main__":
    main()