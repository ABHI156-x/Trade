"""
Tests for Broker Adapters (Zerodha Kite & Angel One SmartAPI).
"""

import unittest
from src.broker.base_broker import Order, OrderType, TransactionType, OrderStatus, ProductType
from src.broker.zerodha_broker import ZerodhaBroker
from src.broker.angel_one_broker import AngelOneBroker


class TestZerodhaBroker(unittest.TestCase):

    def setUp(self):
        self.broker = ZerodhaBroker(is_mock=True)
        self.broker.authenticate()

    def test_mock_authentication(self):
        self.assertTrue(self.broker._authenticated)

    def test_place_mock_order(self):
        order = Order(
            symbol="RELIANCE",
            transaction_type=TransactionType.BUY,
            quantity=10,
            price=2500.0,
            order_type=OrderType.LIMIT
        )
        placed = self.broker.place_order(order)
        self.assertEqual(placed.status, OrderStatus.COMPLETE)
        self.assertIsNotNone(placed.order_id)
        self.assertEqual(placed.filled_quantity, 10)

        # Check positions updated
        positions = self.broker.get_positions()
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["symbol"], "RELIANCE")
        self.assertEqual(positions[0]["quantity"], 10)

    def test_cancel_order(self):
        order = Order(
            symbol="INFY",
            transaction_type=TransactionType.BUY,
            quantity=5,
            price=1500.0,
            status=OrderStatus.OPEN
        )
        order.order_id = "TEST-ORDER-1"
        self.broker._orders["TEST-ORDER-1"] = order

        success = self.broker.cancel_order("TEST-ORDER-1")
        self.assertTrue(success)
        self.assertEqual(order.status, OrderStatus.CANCELLED)


class TestAngelOneBroker(unittest.TestCase):

    def setUp(self):
        self.broker = AngelOneBroker(is_mock=True)
        self.broker.authenticate()

    def test_mock_authentication(self):
        self.assertTrue(self.broker._authenticated)

    def test_place_mock_order(self):
        order = Order(
            symbol="TCS",
            transaction_type=TransactionType.BUY,
            quantity=2,
            price=3500.0,
            order_type=OrderType.MARKET
        )
        placed = self.broker.place_order(order)
        self.assertEqual(placed.status, OrderStatus.COMPLETE)
        self.assertEqual(placed.filled_quantity, 2)


if __name__ == "__main__":
    unittest.main()
