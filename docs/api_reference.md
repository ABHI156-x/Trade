# Indian Day Trader – API Reference

Complete API reference for core classes, functions, and data structures.

---

## 1. Market Data (`src.market_data`)

### `TickData`
`src.market_data.websocket_feed.TickData`
Standard data structure for incoming market ticks.
- **Attributes**:
  - `symbol` (*str*): Stock ticker (e.g. `"RELIANCE"`).
  - `timestamp` (*datetime*): Tick arrival timestamp.
  - `ltp` (*float*): Last traded price.
  - `volume` (*int*): Traded volume in this tick.
  - `bid_price` (*float*): Best bid price.
  - `ask_price` (*float*): Best ask price.
  - `exchange` (*str*): `"NSE"` or `"BSE"`.

### `CandleAggregator`
`src.market_data.websocket_feed.CandleAggregator(timeframe_minutes=5)`
Aggregates tick streams into discrete timeframe OHLCV candles.
- **Methods**:
  - `process_tick(tick: TickData) -> Optional[dict]`: Ingests a tick. Returns a completed candle dict if interval rolled over, else `None`.
  - `get_current_candle(symbol: str) -> Optional[dict]`: Retrieves the current forming candle.

### `SimulatedWebSocketFeed`
`src.market_data.websocket_feed.SimulatedWebSocketFeed(timeframe_minutes=5, tick_interval_sec=0.5, speed_factor=1.0, historical_df=None)`
High-performance simulator generating realistic synthetic ticks or replaying historical CSVs.
- **Methods**:
  - `subscribe(symbols: List[str])`: Add symbols to subscription list.
  - `unsubscribe(symbols: List[str])`: Remove symbols.
  - `connect()`: Start feed worker thread.
  - `disconnect()`: Stop feed worker thread.
  - `on_tick(callback)`: Register tick listener callback.
  - `on_candle_close(callback)`: Register candle close listener callback.

### `DataSourceVerifier`
`src.market_data.data_source_verifier.DataSourceVerifier`
Checks upstream historical data provider limits before dispatching queries.
- **Methods**:
  - `validate_date_range(start_date, end_date, interval="5m") -> Tuple[bool, str]`: Enforces yfinance interval limits (30d for 1m, 60d for 5m).
  - `get_source_limitations() -> dict`: Returns structured metadata of data provider limitations.

---

## 2. Scanner & Analysis (`src.scanner`, `src.analysis`)

### `scan_stocks(df: pd.DataFrame) -> pd.DataFrame`
`src.scanner.stock_scanner.scan_stocks`
Scans a multi-stock DataFrame and ranks setups by composite technical score (0 to 100).
- **Returns**: DataFrame with columns `symbol, exchange, close, ema_9, ema_21, rsi, signal, score`.

### `calculate_indicators_by_symbol(df, ema_periods=(9, 21, 50), ...)`
`src.analysis.indicators.calculate_indicators_by_symbol`
Calculates EMA, SMA, RSI, and MACD indicators independently for every symbol without cross-contamination.

---

## 3. Backtesting & Causal Validation (`src.backtesting`)

### `validate_strategy(...)`
`src.backtesting.strategy_validator.validate_strategy`
Performs chronological train/test validation with automatic data-leakage auditing.
- **Parameters**:
  - `df` (*pd.DataFrame*): Historical OHLCV market data.
  - `train_ratio` (*float*): Fraction of data for training (default `0.70`).
  - `initial_capital` (*float*): Starting account balance (default `10000`).
  - `risk_per_trade` (*float*): Maximum risk in INR per trade (default `100`).
- **Returns**: Dictionary with `train_period`, `test_period`, `train_report`, `test_report`, and `data_leakage_checks`.

### `check_data_leakage(train_data, test_data) -> dict`
`src.backtesting.strategy_validator.check_data_leakage`
Verifies that `max(train_timestamp) < min(test_timestamp)` and timestamp overlap is 0.

### `WalkForwardBacktester(n_splits=5, test_ratio=0.2)`
`src.backtesting.out_of_sample_backtester.WalkForwardBacktester`
Executes rolling out-of-sample folds across the dataset.

---

## 4. Risk Management (`src.risk`)

### `DailyRiskGuard(max_daily_loss=500, max_trades=3)`
`src.risk.daily_risk_guard.DailyRiskGuard`
Enforces daily intraday loss and trade count limits.
- **Methods**:
  - `can_take_trade(unrealized_pnl=0) -> Tuple[bool, str]`: Validates whether risk budget allows entry.
  - `record_trade(pnl: float)`: Records completed trade P&L.
  - `reset()`: Resets counters for new market day.

### `AdvancedRiskGuard(...)`
`src.risk.advanced_risk_guard.AdvancedRiskGuard`
Extends `DailyRiskGuard` with portfolio exposure caps, consecutive loss circuit breakers, and sector limits.
- **Parameters**:
  - `max_consecutive_losses` (*int*): Halts entries after N back-to-back losses.
  - `max_exposure_percent` (*float*): Maximum committed capital fraction (default `0.5`).
  - `sector_caps` (*dict*): Dictionary mapping sector names to max positions.

### `IndexCircuitBreaker(index_open_price)`
`src.risk.circuit_breaker.IndexCircuitBreaker`
Tracks index moves against SEBI's 10%, 15%, and 20% thresholds and reports mandatory halt durations.

---

## 5. Paper Trading (`src.paper_trading`)

### `LivePaperTrader(...)`
`src.paper_trading.live_paper_trader.LivePaperTrader`
Event-driven engine consuming ticks and completed candles to run live paper trading.
- **Methods**:
  - `start()`: Subscribes and connects feed.
  - `stop()`: Shuts down feed and stops trading.
  - `get_status() -> dict`: Returns live telemetry, broker status, and open positions.

### `PortfolioPaperBroker(...)`
`src.paper_trading.portfolio_paper_broker.PortfolioPaperBroker`
Multi-asset simulated broker with regulatory transaction cost modeling.
- **Methods**:
  - `open_position(symbol, entry_price, stop_loss, target, timestamp, ...)`: Enters trade if risk budget permits.
  - `close_position(symbol, exit_price, timestamp, reason)`: Closes open position and logs P&L.
  - `get_report(current_prices=None) -> dict`: Returns equity, balances, and win/loss statistics.

---

## 6. Broker Layer & Order Execution Engine (`src.broker`, `src.execution`)

### `Order`
`src.broker.base_broker.Order`
Standardized order representation supporting `BUY`, `SELL`, `MARKET`, `LIMIT`, `SL`, `SL-M`, `MIS`, `CNC`.

### `ZerodhaBroker(api_key, api_secret, access_token, is_mock=True)`
`src.broker.zerodha_broker.ZerodhaBroker`
Adapter for Zerodha Kite Connect API 3.
- **Methods**:
  - `authenticate() -> bool`: Validates API session.
  - `place_order(order: Order) -> Order`: Routes order to Kite or mock simulator.
  - `cancel_order(order_id: str) -> bool`: Cancels open order.
  - `get_positions() -> List[dict]`: Retrieves current broker positions.

### `AngelOneBroker(api_key, client_code, jwt_token, is_mock=True)`
`src.broker.angel_one_broker.AngelOneBroker`
Adapter for Angel One SmartAPI.

### `OrderExecutionEngine(...)`
`src.execution.order_execution_engine.OrderExecutionEngine`
High-safety gatekeeper for broker order placement.
- **Parameters**:
  - `broker` (*BaseBroker*): Target broker adapter.
  - `risk_guard` (*AdvancedRiskGuard*): Associated risk guard.
  - `max_order_value` (*float*): Single order fat-finger cap (default `₹50,000`).
  - `max_daily_turnover` (*float*): Cumulative daily turnover limit (default `₹200,000`).
  - `dry_run` (*bool*): If `True`, intercepts before sending live network packet.
- **Methods**:
  - `disengage_kill_switch(confirmation: str) -> bool`: Disengages safety kill switch if confirmation is `"I_CONFIRM_LIVE_TRADING"`.
  - `execute_order(order: Order, current_price: float) -> Order`: Validates all safety tiers and dispatches order.

---

## 7. Telemetry & Alerts (`src.dashboard`, `src.alerts`)

### `PaperTradingDashboard`
`src.dashboard.dashboard.PaperTradingDashboard`
Renders formatted ASCII snapshot of balances, risk parameters, and sparkline equity curve.
- **Methods**:
  - `update_equity(equity: float)`: Appends equity mark.
  - `render(broker_report, risk_report=None) -> str`: Builds terminal dashboard representation.

### `AlertManager(notifiers=None)`
`src.alerts.alert_manager.AlertManager`
Dispatches signal, risk, and trade alerts to configured destinations (`ConsoleNotifier`, `EmailNotifier`).
