"""
Tests for WebSocket Market Data Feed & Candle Aggregator.
"""

import unittest
from datetime import datetime, timedelta
from src.market_data.websocket_feed import (
    TickData,
    CandleAggregator,
    SimulatedWebSocketFeed,
    LiveBrokerWebSocketFeed
)


class TestCandleAggregator(unittest.TestCase):

    def setUp(self):
        self.agg = CandleAggregator(timeframe_minutes=5)

    def test_single_tick_does_not_close_candle(self):
        t0 = datetime(2026, 11, 4, 9, 15, 10)
        tick = TickData(symbol="RELIANCE", timestamp=t0, ltp=2500.0, volume=10)
        closed = self.agg.process_tick(tick)
        self.assertIsNone(closed)

        running = self.agg.get_current_candle("RELIANCE")
        self.assertIsNotNone(running)
        self.assertEqual(running["open"], 2500.0)
        self.assertEqual(running["high"], 2500.0)
        self.assertEqual(running["close"], 2500.0)
        self.assertEqual(running["volume"], 10)

    def test_multiple_ticks_update_ohlcv(self):
        t0 = datetime(2026, 11, 4, 9, 15, 10)
        t1 = datetime(2026, 11, 4, 9, 16, 0)
        t2 = datetime(2026, 11, 4, 9, 18, 30)

        self.agg.process_tick(TickData(symbol="TCS", timestamp=t0, ltp=3500.0, volume=50))
        self.agg.process_tick(TickData(symbol="TCS", timestamp=t1, ltp=3520.0, volume=100))
        self.agg.process_tick(TickData(symbol="TCS", timestamp=t2, ltp=3490.0, volume=75))

        running = self.agg.get_current_candle("TCS")
        self.assertEqual(running["open"], 3500.0)
        self.assertEqual(running["high"], 3520.0)
        self.assertEqual(running["low"], 3490.0)
        self.assertEqual(running["close"], 3490.0)
        self.assertEqual(running["volume"], 225)

    def test_candle_boundary_rollover_finalizes_previous_candle(self):
        t0 = datetime(2026, 11, 4, 9, 15, 0)
        t_next = datetime(2026, 11, 4, 9, 20, 0)  # Next 5-min interval

        self.agg.process_tick(TickData(symbol="INFY", timestamp=t0, ltp=1500.0, volume=100))
        closed = self.agg.process_tick(TickData(symbol="INFY", timestamp=t_next, ltp=1510.0, volume=50))

        self.assertIsNotNone(closed)
        self.assertEqual(closed["open"], 1500.0)
        self.assertEqual(closed["close"], 1500.0)
        self.assertEqual(closed["timestamp"], datetime(2026, 11, 4, 9, 15, 0))

        # Check new forming candle
        running = self.agg.get_current_candle("INFY")
        self.assertEqual(running["open"], 1510.0)
        self.assertEqual(running["timestamp"], datetime(2026, 11, 4, 9, 20, 0))


class TestSimulatedWebSocketFeed(unittest.TestCase):

    def test_push_tick_triggers_callbacks(self):
        feed = SimulatedWebSocketFeed(timeframe_minutes=5)
        ticks_received = []
        feed.on_tick(lambda t: ticks_received.append(t))

        tick = TickData(symbol="SBIN", timestamp=datetime.now(), ltp=800.0)
        feed.push_tick(tick)

        self.assertEqual(len(ticks_received), 1)
        self.assertEqual(ticks_received[0].symbol, "SBIN")
        self.assertEqual(ticks_received[0].ltp, 800.0)

    def test_subscribe_unsubscribe(self):
        feed = SimulatedWebSocketFeed()
        feed.subscribe(["RELIANCE", "TCS"])
        self.assertIn("RELIANCE", feed._subscribers)
        self.assertIn("TCS", feed._subscribers)

        feed.unsubscribe(["RELIANCE"])
        self.assertNotIn("RELIANCE", feed._subscribers)
        self.assertIn("TCS", feed._subscribers)

    def test_live_broker_missing_auth_raises(self):
        live_feed = LiveBrokerWebSocketFeed(broker_name="zerodha", api_key="", access_token="")
        with self.assertRaises(ValueError):
            live_feed.connect()


if __name__ == "__main__":
    unittest.main()
