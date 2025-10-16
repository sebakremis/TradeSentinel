# src/price_forecast.py
# modules/price_forecast.py

import numpy as np
import pandas as pd

def project_price_range(data, period_months=1, n_sims=10000):
    """
    Project the price range (min and max) 
    based on Monte Carlo simulations.
    
    Parameters
    ----------
    data : pd.DataFrame
        DataFrame containing columns:
        ['Ticker', 'Close', 'Avg Return', 'Annualized Vol']
    period_months : int
        Time horizon in months (default=1)
    n_sims : int
        Number of Monte Carlo simulations(default=10000)
        
    Returns
    -------
    forecast_df : pd.DataFrame
        DataFrame with columns:
        ['Ticker', 'PrecioActual', 'ForecastMin', 'ForecastMax']
    """
    results = []

    t = period_months / 12  # converted to years



    for _, row in data.iterrows():
        S0 = row['Close']
        mu = row['Avg Return']/100  # Convert percentage to decimal
        sigma = row['Annualized Vol']/100
        print(row['Ticker'], S0, mu, sigma)

        # Simulate end price using Geometric Brownian Motion
        Z = np.random.normal(0, 1, n_sims)
        ST = S0 * np.exp((mu - 0.5 * sigma**2) * t + sigma * np.sqrt(t) * Z)

        forecast_min = np.percentile(ST, 5)
        forecast_max = np.percentile(ST, 95)

        results.append({
            'Ticker': row['Ticker'],
            'Forecast Low': forecast_min,
            'Forecast High': forecast_max,
            'PeriodMonths': period_months
        })

    forecast_df = pd.DataFrame(results)
    return forecast_df
