"""
Live Paper Trader Engine.
Connects real-time WebSocket tick feeds to the StockScanner, Risk Guard,
PortfolioPaperBroker, TradeJournal, AlertManager, and Dashboard.
"""

import threading
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd

from src.market_data.websocket_feed import BaseMarketDataFeed, TickData
from src.scanner.stock_scanner import scan_stocks
from src.paper_trading.portfolio_paper_broker import PortfolioPaperBroker
from src.paper_trading.trade_journal import TradeJournal
from src.alerts.alert_manager import AlertManager
from src.dashboard.dashboard import PaperTradingDashboard
from src.risk.advanced_risk_guard import AdvancedRiskGuard
from src.utils.market_session import is_market_session, is_entry_allowed, is_square_off_time


logger = logging.getLogger("IndianDayTrader.LivePaperTrader")


class LivePaperTrader:
    """
    Real-Time Event-Driven Paper Trading Engine.
    Processes live ticks, builds intraday candles, calculates indicators,
    evaluates strategy signals, checks risk limits, and manages positions.
    """

    def __init__(
        self,
        feed: BaseMarketDataFeed,
        symbols: List[str],
        initial_capital: float = 10000.0,
        risk_per_trade: float = 100.0,
        max_daily_loss: float = 500.0,
        max_trades_per_day: int = 3,
        stop_loss_percent: float = 0.01,
        target_percent: float = 0.02,
        timeframe_minutes: int = 5,
        journal_path: str = "data/trade_journal.csv",
        alert_manager: Optional[AlertManager] = None,
        dashboard: Optional[PaperTradingDashboard] = None,
        enforce_market_hours: bool = False
    ):
        self.feed = feed
        self.symbols = [s.strip().upper() for s in symbols]
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.stop_loss_percent = stop_loss_percent
        self.target_percent = target_percent
        self.timeframe_minutes = timeframe_minutes
        self.enforce_market_hours = enforce_market_hours

        # Broker & Risk Guard
        self.broker = PortfolioPaperBroker(
            initial_capital=initial_capital,
            risk_per_trade=risk_per_trade,
            max_daily_loss=max_daily_loss,
            max_trades_per_day=max_trades_per_day
        )
        self.advanced_risk_guard = AdvancedRiskGuard(
            max_daily_loss=max_daily_loss,
            max_trades=max_trades_per_day,
            total_capital=initial_capital
        )

        # Journal & Alerts
        self.journal = TradeJournal(file_path=journal_path)
        self.alert_manager = alert_manager or AlertManager()
        self.dashboard = dashboard

        # Internal state
        self.candle_history: Dict[str, List[dict]] = {s: [] for s in self.symbols}
        self.current_ltps: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._running = False

        # Register feed callbacks
        self.feed.on_tick(self._handle_tick)
        self.feed.on_candle_close(self._handle_candle_close)

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self.feed.subscribe(self.symbols)
            self.feed.connect()
            logger.info("LivePaperTrader started with symbols: %s", self.symbols)

    def stop(self):
        with self._lock:
            if not self._running:
                return
            self._running = False
            self.feed.disconnect()
            logger.info("LivePaperTrader stopped.")

    def _handle_tick(self, tick: TickData):
        """
        Executed on every incoming market tick.
        Updates LTP and checks intraday stop-loss / target / square-off.
        """
        with self._lock:
            symbol = tick.symbol
            ltp = tick.ltp
            self.current_ltps[symbol] = ltp

            if self.dashboard:
                unrealized = self.broker.calculate_unrealized_pnl(self.current_ltps)
                current_equity = self.broker.balance + self.broker.committed_capital + unrealized
                self.dashboard.update_equity(current_equity)

            # Check open positions on live tick
            if symbol in self.broker.positions:
                pos = self.broker.positions[symbol]
                ts = tick.timestamp

                # Check square off time
                if self.enforce_market_hours and is_square_off_time(ts):
                    self._close_position(symbol, ltp, ts, "SQUARE_OFF")
                    return

                stop_price = pos.get("stop", pos.get("stop_loss"))
                target_price = pos.get("target")

                # Long Stop Loss Check
                if stop_price is not None and ltp <= stop_price:
                    self._close_position(symbol, ltp, ts, "STOP_LOSS")
                # Long Target Check
                elif target_price is not None and ltp >= target_price:
                    self._close_position(symbol, ltp, ts, "TARGET")

    def _close_position(self, symbol: str, price: float, timestamp: datetime, reason: str):
        result = self.broker.close_position(symbol, price, timestamp, reason)
        if result.get("status") in ("CLOSED", "PAPER_POSITION_CLOSED"):
            trade = result.get("trade", result)
            self.journal.save_trade(trade)
            self.advanced_risk_guard.record_trade(trade.get("net_pnl", 0))
            self.alert_manager.trade_alert(trade)
            logger.info("Closed position for %s at %.2f: %s (P&L: %.2f)", symbol, price, reason, trade.get("net_pnl", 0))

    def _handle_candle_close(self, candle: dict):
        """
        Executed whenever an aggregated candle (e.g., 5m) completes.
        Appends to history, runs scanner, and evaluates entry rules.
        """
        with self._lock:
            symbol = candle["symbol"]
            ts = candle["timestamp"]

            if symbol not in self.candle_history:
                self.candle_history[symbol] = []

            self.candle_history[symbol].append(candle)
            # Retain up to 200 bars per symbol for indicator stability
            if len(self.candle_history[symbol]) > 200:
                self.candle_history[symbol].pop(0)

            if self.enforce_market_hours and not is_entry_allowed(ts):
                return

            # Check if we have enough bars to calculate indicators (at least 21 bars for EMA 21)
            history_rows = []
            for s, bars in self.candle_history.items():
                if len(bars) >= 21:
                    history_rows.extend(bars)

            if not history_rows:
                return

            df = pd.DataFrame(history_rows)
            try:
                scanner_report = scan_stocks(df)
            except Exception as e:
                logger.error("Scanner evaluation failed: %s", e)
                return

            if scanner_report.empty:
                return

            # Find top bullish opportunities
            top_matches = scanner_report[scanner_report["signal"] == "BUY"]
            if top_matches.empty:
                return

            for _, match in top_matches.iterrows():
                target_sym = match["symbol"]
                if target_sym in self.broker.positions:
                    continue  # already holding

                entry_price = float(match["close"])
                stop_loss = round(entry_price * (1.0 - self.stop_loss_percent), 2)
                target = round(entry_price * (1.0 + self.target_percent), 2)

                # Pre-trade risk check
                allowed, reason = self.advanced_risk_guard.can_take_trade(
                    unrealized_pnl=self.broker.calculate_unrealized_pnl(self.current_ltps)
                )
                if not allowed:
                    logger.warning("Trade blocked by AdvancedRiskGuard: %s", reason)
                    self.alert_manager.risk_alert(reason)
                    break

                res = self.broker.open_position(
                    symbol=target_sym,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    target=target,
                    timestamp=ts,
                    current_prices=self.current_ltps,
                    exchange=match.get("exchange", "NSE")
                )

                if res.get("status") in ("OPEN", "PAPER_POSITION_OPENED"):
                    trade_info = res.get("position", res)
                    self.alert_manager.trade_alert(trade_info)
                    logger.info("Opened position for %s: Entry=%.2f, SL=%.2f, Tgt=%.2f", target_sym, entry_price, stop_loss, target)

    def get_status(self) -> dict:
        with self._lock:
            broker_report = self.broker.get_report(self.current_ltps)
            risk_report = self.broker.risk_guard.get_report()
            return {
                "running": self._running,
                "symbols": self.symbols,
                "current_ltps": dict(self.current_ltps),
                "broker": broker_report,
                "risk": risk_report
            }
