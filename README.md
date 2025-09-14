# TradeSentinel — Intraday Risk & PnL Monitoring Dashboard

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://tradesentinel-rsnsu2pdi68sqey8ny7wzl.streamlit.app/)

## 📌 Overview
TradeSentinel is a Python-powered dashboard for real-time portfolio monitoring, providing instant insights into PnL, exposure, and risk metrics throughout the trading day. Designed for trading operations and risk management teams, it helps detect limit breaches early and supports informed decision-making.

## 🚀 Features
- **Live market data:** Fetches intraday prices from APIs (Yahoo Finance).
- **PnL tracking:** Calculates mark-to-market PnL by instrument, sector, or portfolio.
- **Risk metrics:** Computes Value-at-Risk (VaR), exposure by asset class, and limit breaches.
- **Interactive dashboard:** Built with Streamlit for intuitive visualization.
- **Alerts:** Email or Slack notifications when thresholds are exceeded.

## 🛠 Tech stack
- **Python:** pandas, numpy, altair, streamlit
- **Data APIs:** Yahoo Finance
- **Deployment:** Streamlit Community Cloud (public), Docker, Heroku, AWS, or Azure

## 📂 Project structure
- **data/** — Sample datasets
- **src/** — Core Python scripts
  - **ensure_data.py** — Market data ingestion
  - **dashboard.py** — App UI and visualization
  - …
- **tests/** — Unit tests
- **requirements.txt** — Python dependencies
- **README.md** — Project documentation
- **LICENSE** — License file

## 📈 Example use case
- **Real-time monitoring:** A trading desk tracks intraday PnL and risk exposure.
- **Limit alerts:** Notifications trigger when VaR exceeds limits or PnL breaches thresholds.
- **Post-trade review:** Historical data supports trend analysis and daily reviews.

---

## 🚀 Launch the dashboard

### Live demo
🌐 Click link to launch TradeSentinel on Streamlit Community Cloud:  
[(https://tradesentinel-rsnsu2pdi68sqey8ny7wzl.streamlit.app/)](https://tradesentinel-rsnsu2pdi68sqey8ny7wzl.streamlit.app/)

No installation required — runs directly in your browser.

### Run locally
```bash
# Clone the repository
git clone https://github.com/sebakremis/TradeSentinel.git
cd TradeSentinel/src

# Install dependencies
pip install -r ../requirements.txt

# Run the dashboard
streamlit run dashboard.py


## 📜 License  
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details. 

---
**Author:** Sebastian Kremis 
**Contact:** skremis@ucm.es

