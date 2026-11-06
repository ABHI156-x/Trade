"""
Tests for LivePaperTrader with real-time feed integration.
"""

import os
import unittest
from datetime import datetime, timedelta
import pandas as pd

from src.market_data.websocket_feed import SimulatedWebSocketFeed, TickData
from src.paper_trading.live_paper_trader import LivePaperTrader
from src.alerts.alert_manager import AlertManager


class TestLivePaperTrader(unittest.TestCase):

    def setUp(self):
        self.journal_path = "data/test_live_journal.csv"
        if os.path.exists(self.journal_path):
            os.remove(self.journal_path)

        self.feed = SimulatedWebSocketFeed(timeframe_minutes=5)
        self.alert_mgr = AlertManager()
        self.trader = LivePaperTrader(
            feed=self.feed,
            symbols=["INFY", "TCS"],
            initial_capital=10000.0,
            risk_per_trade=100.0,
            max_daily_loss=500.0,
            max_trades_per_day=3,
            stop_loss_percent=0.01,
            target_percent=0.02,
            journal_path=self.journal_path,
            alert_manager=self.alert_mgr,
            enforce_market_hours=False
        )

    def tearDown(self):
        self.trader.stop()
        if os.path.exists(self.journal_path):
            os.remove(self.journal_path)

    def test_tick_updates_ltp(self):
        t0 = datetime(2026, 11, 4, 9, 15, 0)
        tick = TickData(symbol="INFY", timestamp=t0, ltp=1500.0)
        self.trader._handle_tick(tick)

        status = self.trader.get_status()
        self.assertEqual(status["current_ltps"].get("INFY"), 1500.0)

    def test_tick_triggers_stop_loss(self):
        t0 = datetime(2026, 11, 4, 9, 15, 0)
        # Manually open a position
        self.trader.broker.open_position(
            symbol="INFY",
            entry_price=1000.0,
            stop_loss=990.0,
            target=1020.0,
            timestamp=t0
        )
        self.assertIn("INFY", self.trader.broker.positions)

        # Tick at 989 falls below stop_loss (990)
        t1 = datetime(2026, 11, 4, 9, 16, 0)
        tick_sl = TickData(symbol="INFY", timestamp=t1, ltp=989.0)
        self.trader._handle_tick(tick_sl)

        self.assertNotIn("INFY", self.trader.broker.positions)
        self.assertEqual(len(self.trader.broker.trade_history), 1)
        self.assertEqual(self.trader.broker.trade_history[0]["reason"], "STOP_LOSS")

    def test_tick_triggers_target(self):
        t0 = datetime(2026, 11, 4, 9, 15, 0)
        self.trader.broker.open_position(
            symbol="TCS",
            entry_price=3000.0,
            stop_loss=2970.0,
            target=3060.0,
            timestamp=t0
        )
        self.assertIn("TCS", self.trader.broker.positions)

        # Tick at 3065 reaches target (3060)
        t1 = datetime(2026, 11, 4, 9, 17, 0)
        tick_target = TickData(symbol="TCS", timestamp=t1, ltp=3065.0)
        self.trader._handle_tick(tick_target)

        self.assertNotIn("TCS", self.trader.broker.positions)
        self.assertEqual(len(self.trader.broker.trade_history), 1)
        self.assertEqual(self.trader.broker.trade_history[0]["reason"], "TARGET")
        self.assertGreater(self.trader.broker.trade_history[0]["net_pnl"], 0)


if __name__ == "__main__":
    unittest.main()
