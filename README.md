# TradeSentinel — PortfolioAnalytics

[🚀 Open demo version in Streamlit](https://tradesentinel-rsnsu2pdi68sqey8ny7wzl.streamlit.app/)

* This repository is the private development repo for v1.0.0.

## 📌 Overview
`TradeSentinel` is a Python-powered dashboard for real-time portfolio monitoring, providing instant insights into PnL, exposure, and risk metrics throughout the trading day. Designed for trading operations and risk management teams, it helps detect limit breaches early and supports informed decision-making.

## 🚀 Features
- **Live market data:** Fetches prices from APIs (Yahoo Finance).

- **PnL tracking:** Calculates mark-to-market PnL by instrument, sector, or portfolio.
   * Note: For historical data, `TradeSentinel` uses adjusted close prices (via auto_adjust=True) to account for dividends and splits. This ensures that PnL calculations reflect total return and avoids artificial price drops on dividend dates.    
- **Risk metrics:** Computes Value-at-Risk (VaR), exposure by asset class, and limit breaches.
- **Interactive dashboard:** Built with Streamlit for intuitive visualization.

## 🛠 Tech stack
- **Python:** `pandas`, `numpy`, `altair`, `streamlit`, `plotly`
- **Data APIs:** `Yahoo Finance`
- **Deployment:** `Streamlit Community Cloud`

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
- **Comprehensive portfolio analysis**: View and explore portfolio metrics and visualizations over a selected time horizon. Analyze historical performance, sector allocation, and asset distribution trends to support medium‑ and long‑term investment decisions.
- **On-demand CSV snapshots**: Export the current portfolio metrics view to CSV for quick sharing, further analysis, or archiving as a daily snapshot.
- **Foundation for scalable financial platforms**: Use `TradeSentinel`’s modular architecture as the starting point for building more complex solutions — for example, integrating with broker APIs for live order execution, adding multi‑asset risk engines, or connecting to internal data warehouses for firm‑wide exposure reporting. Its clean separation between data ingestion, analytics, and visualization makes it easy to extend into a full‑scale portfolio management or risk monitoring system.

---

## 🚀 Launch the dashboard

### Live demo
<a href="https://tradesentinel-rsnsu2pdi68sqey8ny7wzl.streamlit.app/" target="_blank">🌐 Click here to launch TradeSentinel demo on Streamlit Community Cloud</a>  

_No installation required — runs directly in your browser._  

*(Tip: On GitHub, links always open in the same tab. Right‑click and choose “Open link in new tab” if you prefer.)*


## 📜 License

This project is currently developed in a **private repository** and is not publicly distributed.  
The codebase includes the [MIT License](LICENSE) to ensure that, if the repository is made public in the future, usage terms are already defined.  

- While the repository remains private, the license has no practical effect since access is restricted.  
- If the project is later published, the MIT License will apply, granting broad rights to use, modify, and distribute the software with attribution.  

---
**Author:** Sebastian Kremis 
**Contact:** skremis@ucm.es

