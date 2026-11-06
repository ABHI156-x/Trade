
import unittest

from datetime import datetime

from src.utils.market_session import (
    is_market_session,
    is_entry_allowed,
    is_square_off_time
)

from src.backtesting.execution import check_exit_conditions
from src.risk.daily_risk_guard import DailyRiskGuard


class TestMarketSession(unittest.TestCase):

    def test_market_open(self):
        timestamp = datetime(2026, 11, 4, 9, 15)
        self.assertTrue(is_market_session(timestamp))

    def test_outside_market(self):
        timestamp = datetime(2026, 11, 4, 16, 0)
        self.assertFalse(is_market_session(timestamp))

    def test_entry_cutoff(self):
        timestamp = datetime(2026, 11, 4, 15, 16)
        self.assertFalse(is_entry_allowed(timestamp))

    def test_square_off(self):
        timestamp = datetime(2026, 11, 4, 15, 25)
        self.assertTrue(is_square_off_time(timestamp))


class TestExecution(unittest.TestCase):

    def setUp(self):
        self.position = {
            "entry": 1000,
            "stop": 990,
            "target": 1020,
            "quantity": 10
        }

    def test_stop_loss_gap(self):

        candle = {
            "open": 985,
            "high": 995,
            "low": 980,
            "close": 990
        }

        result = check_exit_conditions(candle, self.position)

        self.assertEqual(result, (985, "STOP_LOSS_GAP"))

    def test_normal_stop_loss(self):

        candle = {
            "open": 1000,
            "high": 1005,
            "low": 988,
            "close": 995
        }

        result = check_exit_conditions(candle, self.position)

        self.assertEqual(result, (990, "STOP_LOSS"))

    def test_target(self):

        candle = {
            "open": 1000,
            "high": 1025,
            "low": 995,
            "close": 1020
        }

        result = check_exit_conditions(candle, self.position)

        self.assertEqual(result, (1020, "TARGET"))

    def test_stop_has_priority(self):

        candle = {
            "open": 1000,
            "high": 1025,
            "low": 985,
            "close": 1010
        }

        result = check_exit_conditions(candle, self.position)

        self.assertEqual(result, (990, "STOP_LOSS"))


class TestDailyRiskGuard(unittest.TestCase):

    def test_daily_loss_limit(self):

        guard = DailyRiskGuard(max_daily_loss=500, max_trades=3)

        guard.record_trade(-500)

        allowed, message = guard.can_take_trade()

        self.assertFalse(allowed)
        self.assertEqual(message, "Daily loss limit reached.")

    def test_trade_limit(self):

        guard = DailyRiskGuard(max_daily_loss=500, max_trades=2)

        guard.record_trade(50)
        guard.record_trade(50)

        allowed, message = guard.can_take_trade()

        self.assertFalse(allowed)
        self.assertEqual(message, "Maximum daily trades reached.")

    def test_completed_trade_always_recorded(self):

        guard = DailyRiskGuard(max_daily_loss=500, max_trades=1)

        guard.record_trade(-100)

        # A completed trade must still be recorded.
        guard.record_trade(-50)

        report = guard.get_report()

        self.assertEqual(report["trades_taken"], 2)
        self.assertEqual(report["realized_pnl"], -150)

    def test_daily_reset(self):

        guard = DailyRiskGuard(max_daily_loss=500, max_trades=3)

        guard.record_trade(-200)
        guard.reset()

        report = guard.get_report()

        self.assertEqual(report["realized_pnl"], 0)
        self.assertEqual(report["trades_taken"], 0)


if __name__ == "__main__":
    unittest.main()
