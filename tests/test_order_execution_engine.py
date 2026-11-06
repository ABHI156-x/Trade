"""
Safety Tests for OrderExecutionEngine.
"""

import unittest
from datetime import datetime
from src.broker.base_broker import Order, OrderType, TransactionType, OrderStatus
from src.broker.zerodha_broker import ZerodhaBroker
from src.risk.advanced_risk_guard import AdvancedRiskGuard
from src.execution.order_execution_engine import OrderExecutionEngine


class TestOrderExecutionEngine(unittest.TestCase):

    def setUp(self):
        self.broker = ZerodhaBroker(is_mock=True)
        self.risk_guard = AdvancedRiskGuard(max_daily_loss=500.0, max_trades=3)
        self.engine = OrderExecutionEngine(
            broker=self.broker,
            risk_guard=self.risk_guard,
            max_order_value=50000.0,
            max_order_quantity=100,
            max_daily_turnover=100000.0,
            dry_run=True,
            enforce_market_hours=False
        )

    def test_dry_run_execution_succeeds(self):
        order = Order(
            symbol="INFY",
            transaction_type=TransactionType.BUY,
            quantity=10,
            price=1500.0
        )
        res = self.engine.execute_order(order, current_price=1500.0)
        self.assertEqual(res.status, OrderStatus.COMPLETE)
        self.assertEqual(self.engine.daily_turnover, 15000.0)
        self.assertEqual(len(self.engine.audit_log), 1)
        self.assertTrue(self.engine.audit_log[0]["passed_safety"])

    def test_fat_finger_order_value_rejected(self):
        order = Order(
            symbol="RELIANCE",
            transaction_type=TransactionType.BUY,
            quantity=50,
            price=2500.0  # 50 * 2500 = 125,000 > 50,000 limit
        )
        res = self.engine.execute_order(order, current_price=2500.0)
        self.assertEqual(res.status, OrderStatus.REJECTED)
        self.assertIn("FAT-FINGER BLOCK", res.rejection_reason)

    def test_max_quantity_rejected(self):
        order = Order(
            symbol="SBIN",
            transaction_type=TransactionType.BUY,
            quantity=200,  # exceeds max_order_quantity of 100
            price=100.0
        )
        res = self.engine.execute_order(order, current_price=100.0)
        self.assertEqual(res.status, OrderStatus.REJECTED)
        self.assertIn("exceeds max limit", res.rejection_reason)

    def test_daily_turnover_limit_enforced(self):
        # 1st order: 40,000 turnover
        order1 = Order(symbol="TCS", transaction_type=TransactionType.BUY, quantity=10, price=4000.0)
        res1 = self.engine.execute_order(order1, 4000.0)
        self.assertEqual(res1.status, OrderStatus.COMPLETE)

        # 2nd order: 40,000 turnover (total 80,000)
        order2 = Order(symbol="TCS", transaction_type=TransactionType.BUY, quantity=10, price=4000.0)
        res2 = self.engine.execute_order(order2, 4000.0)
        self.assertEqual(res2.status, OrderStatus.COMPLETE)

        # 3rd order: 30,000 turnover (would reach 110,000 > 100,000 limit)
        order3 = Order(symbol="TCS", transaction_type=TransactionType.BUY, quantity=10, price=3000.0)
        res3 = self.engine.execute_order(order3, 3000.0)
        self.assertEqual(res3.status, OrderStatus.REJECTED)
        self.assertIn("Daily turnover", res3.rejection_reason)

    def test_kill_switch_blocks_live_order(self):
        live_engine = OrderExecutionEngine(
            broker=self.broker,
            dry_run=False,
            enforce_market_hours=False
        )
        self.assertTrue(live_engine.is_kill_switch_engaged)

        order = Order(symbol="INFY", transaction_type=TransactionType.BUY, quantity=5, price=1000.0)
        res = live_engine.execute_order(order, 1000.0)
        self.assertEqual(res.status, OrderStatus.REJECTED)
        self.assertIn("Kill switch is ENGAGED", res.rejection_reason)

        # Disengage with valid confirmation
        ok = live_engine.disengage_kill_switch("I_CONFIRM_LIVE_TRADING")
        self.assertTrue(ok)
        self.assertFalse(live_engine.is_kill_switch_engaged)

        # Now placing order works
        res2 = live_engine.execute_order(order, 1000.0)
        self.assertEqual(res2.status, OrderStatus.COMPLETE)

    def test_risk_guard_daily_loss_blocks_order(self):
        # Trigger daily loss in risk guard
        self.risk_guard.record_trade(-600.0)  # max_daily_loss is 500

        order = Order(symbol="INFY", transaction_type=TransactionType.BUY, quantity=5, price=1000.0)
        res = self.engine.execute_order(order, 1000.0)
        self.assertEqual(res.status, OrderStatus.REJECTED)
        self.assertIn("RISK GUARD BLOCK", res.rejection_reason)


if __name__ == "__main__":
    unittest.main()
