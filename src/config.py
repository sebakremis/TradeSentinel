# src/config.py
from pathlib import Path

# Data sources
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
followed_tickers_file = DATA_DIR / 'followed_tickers.csv'
all_tickers_file = DATA_DIR / 'all_tickers.csv'
stocks_folder = DATA_DIR / 'stocks'
metadata_file = stocks_folder / 'metadata.csv'
PORTFOLIO_FILE = DATA_DIR / 'portfolios.json'
UPDATE_LOG_FILE = stocks_folder / 'updates.json'

# Portfolio defaults
RISK_FREE_RATE = 0.0415 # 10-Year U.S. Treasury Note
BENCHMARK_INDEX = "SPY"
ANNUAL_TRADING_DAYS = 252
DEFAULT_LOOKBACK_PERIOD = "1mo"
FIXED_INTERVAL = "1d"

# Indicators
EMA_PERIOD = 20
CONFIDENCE_LEVEL = 0.95 # used for calculating VAR and for the Monte Carlo Simulation

# Forecasting (Monte Carlo)
FORECAST_HORIZON = 1 # 1 month
N_SIMS = 10000 # number of simulations