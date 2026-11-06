"""
Tests for DataSourceVerifier.
"""

import unittest
from datetime import date, timedelta
from src.market_data.data_source_verifier import DataSourceVerifier, INTERVAL_LIMITS_DAYS


class TestDataSourceVerifier(unittest.TestCase):

    def test_valid_recent_range(self):
        end = date.today()
        start = end - timedelta(days=10)
        valid, msg = DataSourceVerifier.validate_date_range(start, end, "5m")
        self.assertTrue(valid)
        self.assertEqual(msg, "Valid date range")

    def test_invalid_old_range_for_1m(self):
        end = date.today()
        start = end - timedelta(days=45)  # 1m limit is 30 days
        valid, msg = DataSourceVerifier.validate_date_range(start, end, "1m")
        self.assertFalse(valid)
        self.assertIn("30 days", msg)

    def test_start_after_end_rejected(self):
        start = date(2026, 11, 10)
        end = date(2026, 11, 5)
        valid, msg = DataSourceVerifier.validate_date_range(start, end, "5m")
        self.assertFalse(valid)
        self.assertIn("cannot be after", msg)

    def test_unsupported_interval(self):
        valid, msg = DataSourceVerifier.validate_date_range(date.today(), date.today(), "42m")
        self.assertFalse(valid)
        self.assertIn("Unsupported interval", msg)

    def test_limitations_metadata(self):
        meta = DataSourceVerifier.get_source_limitations()
        self.assertIn("intraday_limitations", meta)
        self.assertIn("delays_and_rate_limits", meta)
        self.assertEqual(meta["exchange_suffixes"]["NSE"], ".NS")


if __name__ == "__main__":
    unittest.main()
