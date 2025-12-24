# src/indicators.py
import pandas as pd
import numpy as np

ANNUAL_TRADING_DAYS = 252 
annualized_risk_free_rate = 0.02 

def ema(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """
    Calculates the Exponential Moving Average (EMA).
    """
    # Ensure sorting
    df = df.sort_values(['Ticker', 'Date'])

    # Group by Ticker and apply EMA
    ema_column_name = f'EMA_{n}'
    df[ema_column_name] = df.groupby('Ticker')['close'].transform(
        lambda x: x.ewm(span=n, adjust=False).mean()
    )
    return df

def distance_from_ema(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """
    Calculates the percentage distance between Close price and EMA(n).
    Formula: ((Close - EMA) / EMA) * 100
    """
    # Ensure sorting
    df = df.sort_values(['Ticker', 'Date'])

    # Calculate EMA locally (we don't need to store the raw EMA column permanently)
    ema_series = df.groupby('Ticker')['close'].transform(
        lambda x: x.ewm(span=n, adjust=False).mean()
    )
    
    col_name = f'dist_EMA_{n}'
    
    # Calculate percentage distance
    df[col_name] = ((df['close'] - ema_series) / ema_series) * 100
    
    return df

def calculate_annualized_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates annualized average return, volatility, and Sharpe Ratio.
    """
    
    def aggregate_metrics(group):
        returns = group['dailyReturn'].dropna()
        N = len(returns)
        
        if N < 5: 
            return pd.Series({'avgReturn': np.nan, 'annualizedVol': np.nan, 'sharpeRatio': np.nan})

        # A. Annualized Volatility
        daily_vol = returns.std()
        annualized_vol = daily_vol * np.sqrt(ANNUAL_TRADING_DAYS)
        
        # B. Annualized Return
        total_return = (1 + returns).prod() - 1 
        annualization_factor = ANNUAL_TRADING_DAYS / N 
        annualized_return = (1 + total_return) ** annualization_factor - 1
        
        # C. Sharpe Ratio
        sharpe_ratio = (annualized_return - annualized_risk_free_rate) / annualized_vol if annualized_vol != 0 else np.nan

        return pd.Series({
            'avgReturn': annualized_return * 100,
            'annualizedVol': annualized_vol * 100,
            'sharpeRatio': sharpe_ratio
        })

    if 'dailyReturn' not in df.columns:
        df['dailyReturn'] = df.groupby('Ticker')['close'].pct_change()

    annual_metrics_df = df.groupby('Ticker').apply(aggregate_metrics, include_groups=False).reset_index()

    # Get latest date for merge
    latest_dates = df.groupby('Ticker').tail(1)[['Ticker', 'Date']].reset_index(drop=True)
    
    final_metrics_df = pd.merge(latest_dates, annual_metrics_df, on='Ticker')
    
    return final_metrics_df