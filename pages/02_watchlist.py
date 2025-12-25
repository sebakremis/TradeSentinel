import streamlit as st
st.set_page_config(page_title="📊 TradeSentinel", layout="wide")
import pandas as pd
import numpy as np
import altair as alt
import datetime 
from src.dashboard_core import (
    calculate_all_indicators, get_stock_data, dynamic_filtering,
    load_tickers, add_ticker, confirm_unfollow_dialog, TickerValidationError
)
from src.analytics import calculate_portfolio, project_price_range
from src.dashboard_display import ( 
    highlight_change, display_credits, display_guides_section, display_info_section,
    display_period_selection, display_risk_return_plot
    )
from src.config import EMA_PERIOD

# ----------------------------------------------------------------------
# --- Data Helper Functions ---
# ----------------------------------------------------------------------
dist_EMA_column_name = f'dist_EMA_{EMA_PERIOD}'
DISPLAY_COLUMNS = ['Ticker', 'shortName', 'sector', 'close', dist_EMA_column_name, 'forecastLow', 'forecastHigh', 'avgReturn', 'annualizedVol', 'sharpeRatio']

def _format_final_df(final_df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies rounding and ensures selected columns are present for display.
    """
    df = final_df.copy()

    # Ensure all DISPLAY_COLUMNS are present, filling missing with NaN
    for col in DISPLAY_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    
    # Explicitly ensure 'sector' column is a string type.
    if 'sector' in df.columns:
        df['sector'] = df['sector'].fillna('N/A').astype(str) 
    
    if "marketCap" in df.columns:
        df["marketCap"] = (df["marketCap"] / 1_000_000_000).round(2)  # 2 decimal places
        

    # Select only the display columns
    df = df[DISPLAY_COLUMNS]

    # Apply rounding
    for col in ['close', dist_EMA_column_name, 'startPrice', 'forecastLow', 'forecastHigh', 'divPayout', 'avgReturn', 'annualizedVol', 'sharpeRatio']:
        if col in df.columns:
            df[col] = df[col].round(2)
            
    return df

@st.cache_data
def _cached_forecast(df_snapshot: pd.DataFrame) -> pd.DataFrame:
    return project_price_range(
        df_snapshot[['Ticker', 'close', 'avgReturn', 'annualizedVol']].drop_duplicates(subset=['Ticker'])
    )

def _load_and_process_data(fetch_kwargs: dict) -> (pd.DataFrame, pd.DataFrame, list): 
    
    tickers_df = load_tickers()
    followed_tickers = tickers_df['Ticker'].tolist() if not tickers_df.empty else []

    # load prices and metadata for followed tickers
    df_daily = get_stock_data(
        followed_tickers,
        interval="1d",
        **fetch_kwargs
    )

    if df_daily.empty:
        return pd.DataFrame(), pd.DataFrame(), followed_tickers

    df_daily = calculate_all_indicators(df_daily)

    final_df_unformatted = df_daily.groupby('Ticker').tail(1).copy()

    # Forecast prices
    forecast_df = _cached_forecast(final_df_unformatted)
    final_df_unformatted = final_df_unformatted.merge(
        forecast_df[['Ticker', 'forecastLow', 'forecastHigh']],
        on='Ticker',
        how='left'
    )

    start_prices = df_daily.groupby('Ticker')['close'].first().reset_index()
    start_prices.rename(columns={'close': 'startPrice'}, inplace=True)
    final_df_unformatted = final_df_unformatted.merge(start_prices, on='Ticker', how='left')

    if 'dividends' in df_daily.columns:
        total_dividends = df_daily.groupby('Ticker')['dividends'].sum().reset_index()
        total_dividends.rename(columns={'dividends': 'divPayout'}, inplace=True)
        final_df_unformatted = final_df_unformatted.merge(total_dividends, on='Ticker', how='left')
        final_df_unformatted['divPayout'] = final_df_unformatted['divPayout'].fillna(0)
    else:
        final_df_unformatted['divPayout'] = 0
    if 'sector' in tickers_df.columns and not final_df_unformatted.empty:
        final_df_unformatted = final_df_unformatted.merge(
            tickers_df[['Ticker', 'sector']],
            on='Ticker',
            how='left'
        )
        if 'sector_x' in final_df_unformatted.columns:
            final_df_unformatted['sector'] = final_df_unformatted['sector_y']
            final_df_unformatted.drop(columns=['sector_x', 'sector_y'], inplace=True)

    final_df = _format_final_df(final_df_unformatted)

    return final_df, df_daily, followed_tickers 


# ----------------------------------------------------------------------
# --- UI Rendering Functions ---
# ----------------------------------------------------------------------

def _render_summary_table_and_portfolio(final_df: pd.DataFrame, df_daily: pd.DataFrame):
    """Renders the summary table and portfolio simulation controls."""    
    if final_df.empty:
        st.info("No data available to display in the summary table.")
        return

    # sort data
    sorted_df = final_df.sort_values(by=dist_EMA_column_name, ascending=True)

    # Apply dynamic filtering
    sorted_df = dynamic_filtering(sorted_df, DISPLAY_COLUMNS)

    # --- Risk-Return Plot ---
    display_risk_return_plot(sorted_df)

    # Show active row count 
    if len(sorted_df) != len(final_df):
        st.caption(f"Showing {len(sorted_df)} of {len(final_df)} tickers based on filter.")
    else:
        st.caption(f"Showing all {len(final_df)} tickers.")

    # --- Render Dataframe table ---
    event = st.dataframe(
        sorted_df,
        hide_index=True,
        width='stretch',
        on_select="rerun",
        selection_mode="multi-row", # allow multi-row selection
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "shortName": st.column_config.TextColumn("Short Name", width="medium"),
            "sector": st.column_config.TextColumn("sector"),
            "close": st.column_config.NumberColumn("price", help="Last Close price of the lookback period", format="$%.2f", width="small"),
            dist_EMA_column_name: st.column_config.NumberColumn(f"dist EMA {EMA_PERIOD}", help="Distance to the Exponential Moving Average (%)", format="%.2f%%", width="small"),        
            "forecastLow": st.column_config.NumberColumn("forecastLow", format="$%.2f", width="small"),
            "forecastHigh": st.column_config.NumberColumn("forecastHigh", format="$%.2f",width="small"),                       
            "avgReturn": st.column_config.NumberColumn("AAR%", help="Annualized Average return", format="%.2f%%", width="small"),
            "annualizedVol": st.column_config.NumberColumn("Vol%", help="Annualized Average volatility", format="%.2f%%", width="small"),
            "sharpeRatio": st.column_config.NumberColumn("sharpe", format="%.2f%%", width="small")
        },
    )
    # Get tickers from selected rows.
    selected_indices = event.selection.rows # returns a list of numerical indices
    selected_tickers_df = sorted_df.iloc[selected_indices]

    # Get list of selected tickers
    selected_tickers = selected_tickers_df['Ticker'].tolist()

    # Followed tickers buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Backtest Portfolio", disabled=not selected_tickers):
            if selected_tickers:
                total_investment = 100000  # $100k initial investment
                
                # Pass the full daily data to the calculation function
                portfolio_tuples = calculate_portfolio(selected_tickers, df_daily, total_investment)
                st.session_state['portfolio'] = portfolio_tuples
                st.switch_page("pages/03_backtest.py")
            else:
                st.warning("Please select at least one ticker.")

        st.markdown("Select tickers to backtest a $100 k **equally-weighted portfolio**.")
    with col2:
        if st.button("Unfollow selected tickers", disabled=not selected_tickers):
            confirm_unfollow_dialog(selected_tickers)


# ----------------------------------------------------------------------
# --- Main Dashboard Function ---
# ----------------------------------------------------------------------

def main():
    st.title("📊 Watchlist")

    # User Input for Data Period
    fetch_args = display_period_selection()
      
    # Load and process all data required for the main display
    # Pass the period/date dictionary argument
    final_df, df_daily, followed_tickers = _load_and_process_data(fetch_kwargs=fetch_args)
  
    if not final_df.empty:
        # Render the display sections if data is present
        
        _render_summary_table_and_portfolio(final_df, df_daily) # Pass df_daily to the summary table function
    
    # Info section in sidebar
    display_info_section(df_daily)

    # Guides section in sidebar
    display_guides_section()
        
    # Credits & Navigation
    display_credits()
    if st.button("Go back to main page"):
        st.switch_page("main.py") 
    
if __name__ == "__main__":
    main()