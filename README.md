# TradeSentinel  
**Intraday Risk & PnL Monitoring Dashboard**.[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://tradesentinel-rsnsu2pdi68sqey8ny7wzl.streamlit.app/)

## 📌 Overview  
TradeSentinel is a Python-powered dashboard for **real-time portfolio monitoring**, providing instant insights into PnL, exposure, and risk metrics throughout the trading day.  
Designed for trading operations and risk management teams, it helps detect limit breaches early and supports informed decision-making.  

## 🚀 Features  
- **Live Market Data:** Fetches intraday prices from APIs (Yahoo Finance).  
- **PnL Tracking:** Calculates mark-to-market PnL by instrument, sector, or portfolio.  
- **Risk Metrics:** Computes Value-at-Risk (VaR), exposure by asset class, and limit breaches.  
- **Interactive Dashboard:** Built with `Streamlit` for intuitive visualization.  
- **Alerts:** Email or Slack notifications when thresholds are exceeded.  

## 🛠 Tech Stack  
- **Python:** `pandas`, `numpy`, `plotly`, `streamlit`  
- **Data APIs:** Yahoo Finance 
- **Deployment:** Docker, Heroku, AWS, or Azure  # to be decided

## 📂 Project structure  
- **TradeSentinel/:** Project root directory  
  - **data/:** Sample datasets  
  - **src/:** Core Python scripts  
    - **data_fetch.py:** Market data ingestion  
    - **pnl_calculator.py:** PnL computation logic  
    - **risk_metrics.py:** VaR, exposures, and limits  
    - **dashboard.py:** App UI and visualization  
  - **tests/:** Unit tests  
  - **requirements.txt:** Python dependencies  
  - **README.md:** Project documentation  
  - **LICENSE:** License file  

## 📈 Example use case  
- **Real-time Monitoring:** A trading desk tracks intraday PnL and risk exposure.  
- **Limit Alerts:** Notifications trigger when VaR exceeds limits or PnL breaches thresholds.  
- **Post-Trade Review:** Historical data supports trend analysis and daily reviews.  

## 🚀 Launch the Dashboard Locally

To launch the dashboard locally:

```bash
git clone https://github.com/sebakremis/TradeSentinel.git
cd TradeSentinel/src
pip install -r ../requirements.txt
streamlit run dashboard.py
```
🌐 **Live Demo**

[Click here to launch the TradeSentinel Dashboard](https://tradesentinel-rsnsu2pdi68sqey8ny7wzl.streamlit.app/)

No installation required — runs directly in your browser via Streamlit Community Cloud.



## 📜 License  
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details. 

---
**Author:** Sebastian Kremis 
**Contact:** skremis@ucm.es

