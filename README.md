# Indian Day Trader

An automated, quantitative intraday day trading system specifically engineered for the National Stock Exchange (NSE) and Bombay Stock Exchange (BSE) of India. 

The system features real-time WebSocket market data feeds, dynamic stock scanning, rigorous walk-forward and out-of-sample backtesting, multi-layered risk management, circuit breakers, automated paper trading with live terminal dashboard rendering, and safe broker API adapters (Zerodha Kite Connect & Angel One SmartAPI) guarded by a multi-tier Kill-Switch and Order Execution Engine.

---

## Table of Contents
1. [Core Features](#core-features)
2. [System Architecture](#system-architecture)
3. [Installation & Setup](#installation--setup)
4. [Running the Automated Tests](#running-the-automated-tests)
5. [Quickstart Guide](#quickstart-guide)
   - [1. Data Validation & Leakage Prevention](#1-data-validation--leakage-prevention)
   - [2. Strategy Backtesting & Comparison](#2-strategy-backtesting--comparison)
   - [3. Running the Paper Trading Launcher](#3-running-the-paper-trading-launcher)
6. [Market Data & WebSocket Streaming](#market-data--websocket-streaming)
7. [Risk Management & Safety Gates](#risk-management--safety-gates)
8. [Broker Integration & Live Execution](#broker-integration--live-execution)
9. [Documentation Links](#documentation-links)

---

## Core Features

- **Real-Time WebSocket Market Data**: Event-driven tick engine with thread-safe candle aggregation (1m, 5m, 15m), automated reconnection with exponential backoff, and mock/simulated streaming modes.
- **Stock Scanner**: Real-time intraday scanner evaluating EMA trends (EMA 9/21), RSI momentum, MACD cross, and volume surges to generate directional trading signals.
- **Multi-Layer Risk Management**:
  - `DailyRiskGuard`: Enforces hard INR daily loss limits and maximum intraday trades.
  - `AdvancedRiskGuard`: Adds portfolio exposure caps, consecutive loss circuit breakers, and per-sector concentration limits.
  - `IndexCircuitBreaker`: Coordinates halts with NSE/BSE index-level market-wide circuit breaker thresholds (10%, 15%, 20%).
- **Causal Strategy Validation**: Out-of-sample and walk-forward validation engines with zero-data-leakage verification guarantees between train and test datasets.
- **Paper Trading Engine**: `LivePaperTrader` and `AutoPaperTrader` executing simulated trades with realistic Indian equity transaction costs (STT, GST, SEBI turnover fees, exchange transaction charges, stamp duty, brokerage, and slippage).
- **Interactive Terminal Dashboard**: Real-time ASCII dashboard with equity curve visualization, open position tracking, and daily risk telemetry.
- **Broker Integration Layer**: Production-ready API adapters for Zerodha Kite Connect and Angel One SmartAPI, guarded by `OrderExecutionEngine` with a software Kill-Switch and fat-finger limits.

---

## System Architecture

```
                    ┌─────────────────────────┐
                    │ Real-Time WebSocket Feed│
                    │  (Zerodha / Simulated)  │
                    └───────────┬─────────────┘
                                │ Ticks
                                ▼
                    ┌─────────────────────────┐
                    │    Candle Aggregator    │ (1m / 5m OHLCV)
                    └───────────┬─────────────┘
                                │ Completed Candles
                                ▼
                    ┌─────────────────────────┐
                    │   Intraday Stock Scanner│ (EMA / RSI / MACD)
                    └───────────┬─────────────┘
                                │ Entry Signals
                                ▼
                    ┌─────────────────────────┐
                    │   Advanced Risk Guard   │ (Daily Loss / Consecutive Losses)
                    └───────────┬─────────────┘
                                │ Approved Orders
                                ▼
         ┌─────────────────────────────────────────────────┐
         │                                                 │
         ▼                                                 ▼
┌─────────────────────────┐               ┌─────────────────────────────────┐
│   Live Paper Broker     │               │    Order Execution Engine       │
│  (Simulation / Journal) │               │ (Kill-Switch / Pre-Trade Checks)│
└─────────────────────────┘               └────────────────┬────────────────┘
                                                           │ Live Orders
                                                           ▼
                                          ┌─────────────────────────────────┐
                                          │ Broker API (Zerodha / AngelOne) │
                                          └─────────────────────────────────┘
```

For comprehensive details, see [docs/architecture.md](docs/architecture.md).

---

## Installation & Setup

### Prerequisites
- Python 3.10+ (Tested up to Python 3.15)
- Windows / macOS / Linux

### Setup Instructions

1. Clone or navigate to the repository:
   ```bash
   cd Indian-Day-Trader
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows (cmd):
   venv\Scripts\activate.bat
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest
   ```

4. Configure environment variables in `.env`:
   ```ini
   BROKER_NAME=zerodha
   BROKER_API_KEY=your_kite_api_key
   BROKER_ACCESS_TOKEN=your_access_token
   LIVE_ORDER_EXECUTION_ENABLED=false
   ```

---

## Running the Automated Tests

The test suite contains **275+ unit and integration tests** verifying all core components.

Run the test suite via `pytest`:
```bash
pytest tests -v
```

Or run via Python's standard `unittest`:
```bash
python -m unittest discover -s tests -v
```

All tests run without requiring live broker credentials or active market hours.

---

## Quickstart Guide

### 1. Data Validation & Leakage Prevention
Verify out-of-sample data splitting and confirm zero data leakage:
```bash
python test_strategy_validation.py
```

### 2. Strategy Backtesting & Comparison
Run portfolio-level strategy backtesting with complete cost modeling:
```bash
python test_portfolio_dashboard.py
```

### 3. Running the Paper Trading Launcher
Launch real-time or replay paper trading via `scripts/run_paper_trader.py`:

- **Replay Mode** (from historical CSV with accelerated speed):
  ```bash
  python scripts/run_paper_trader.py --mode replay --speed 10.0
  ```

- **Simulated Real-Time Mode** (synthetic ticks adhering to 0.05 NSE tick size):
  ```bash
  python scripts/run_paper_trader.py --mode simulated --symbols "RELIANCE,TCS,INFY,HDFCBANK"
  ```

- **Live Broker Feed Mode**:
  ```bash
  python scripts/run_paper_trader.py --mode live --symbols "RELIANCE,TCS"
  ```

---

## Market Data & WebSocket Streaming

- **Historical Fetchers**: `fetch_nse_ohlcv` and `fetch_bse_ohlcv` retrieve historical daily/intraday candles from Yahoo Finance with standard `.NS` and `.BO` suffixes.
- **Data Limitations**: Yahoo Finance provides a maximum of 30 days of 1-minute data and 60 days of 5-minute data. `DataSourceVerifier` automatically validates query ranges against these upstream limits.
- **Real-Time WebSocket**: `SimulatedWebSocketFeed` and `LiveBrokerWebSocketFeed` push millisecond ticks to `CandleAggregator`, building standardized OHLCV candles with automatic period finalization.

---

## Risk Management & Safety Gates

1. **Daily Loss Cut-Off**: Immediate liquidation and trading halt upon exceeding INR limit (default: ₹500).
2. **Consecutive Loss Breaker**: Halts new entries after N consecutive losing trades (default: 3).
3. **Session Timing**: Blocks new entries after 15:15 IST and triggers auto-square-off at 15:20 IST before market close (15:30 IST).
4. **Index Circuit Breakers**: Tracks Nifty 50 / Sensex daily movement against official SEBI thresholds (10%, 15%, 20%).
5. **Execution Kill-Switch**: Requires explicit authorization (`I_CONFIRM_LIVE_TRADING`) and sets strict per-order value limits (fat-finger protection).

---

## Documentation Links

- [docs/architecture.md](docs/architecture.md) – Detailed system architecture, data pipelines, and sequence diagrams.
- [docs/api_reference.md](docs/api_reference.md) – Comprehensive API reference for classes, functions, and models.
- [docs/broker_integration.md](docs/broker_integration.md) – Official Indian broker API integration guide & live order execution safety guidelines.
