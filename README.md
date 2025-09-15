# TradeSentinel — Intraday Risk & PnL Monitoring Dashboard

<a href="https://tradesentinel-rsnsu2pdi68sqey8ny7wzl.streamlit.app/" target="_blank">
  <img src="https://static.streamlit.io/badges/streamlit_badge_black_white.svg" alt="Open in Streamlit">
</a>

## 📌 Overview
TradeSentinel is a Python-powered dashboard for real-time portfolio monitoring, providing instant insights into PnL, exposure, and risk metrics throughout the trading day. Designed for trading operations and risk management teams, it helps detect limit breaches early and supports informed decision-making.

## 🚀 Features
- **Live market data:** Fetches intraday prices from APIs (Yahoo Finance).
- **PnL tracking:** Calculates mark-to-market PnL by instrument, sector, or portfolio.
- **Risk metrics:** Computes Value-at-Risk (VaR), exposure by asset class, and limit breaches.
- **Interactive dashboard:** Built with Streamlit for intuitive visualization.

## 🛠 Tech stack
- **Python:** pandas, numpy, altair, streamlit
- **Data APIs:** Yahoo Finance
- **Deployment:** Streamlit Community Cloud

## 📂 Project structure
- **data/** — Sample datasets  
- **src/** — Core Python scripts  
  - **ensure_data.py** — Market data ingestion  
  - **dashboard.py** — App UI and visualization  
  - *(other supporting modules)*  
- **tests/** — Unit tests  
- **requirements.txt** — Python dependencies  
- **README.md** — Project documentation  
- **LICENSE** — License file  


## 📈 Example use case
- **Intraday PnL tracking**: Monitor live portfolio PnL and key metrics during market hours to quickly spot drawdowns or performance spikes.
- **On-demand CSV snapshots**: Export the current portfolio metrics view to CSV for quick sharing, further analysis, or archiving as a daily snapshot.

---

## 🚀 Launch the dashboard

### Live demo
<a href="https://tradesentinel-rsnsu2pdi68sqey8ny7wzl.streamlit.app/" target="_blank">
  🌐 Click here to launch TradeSentinel on Streamlit Community Cloud
</a>  
No installation required — runs directly in your browser.

### Alternatively, clone the repo and run `dashboard.py` locally:
```bash
# Clone the repository
git clone https://github.com/sebakremis/TradeSentinel.git
cd TradeSentinel/src

# Install dependencies
pip install -r ../requirements.txt

# Run the dashboard
streamlit run dashboard.py
```
* **To exit a dashboard.py local session**: close the Dashboard tab & press `Ctrl + C` in your terminal.
## 📜 License  
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details. 

---
**Author:** Sebastian Kremis 
**Contact:** skremis@ucm.es

