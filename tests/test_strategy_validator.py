"""
Tests for strategy_validator and data leakage checks.
"""

import unittest
import pandas as pd
from src.backtesting.strategy_validator import validate_strategy, check_data_leakage


class TestStrategyValidator(unittest.TestCase):

    def setUp(self):
        # Generate 20 candles for 2 symbols
        rows = []
        base_time = pd.Timestamp("2026-11-04 09:15:00")
        for sym in ["INFY", "TCS"]:
            for i in range(20):
                rows.append({
                    "timestamp": base_time + pd.Timedelta(minutes=5 * i),
                    "symbol": sym,
                    "open": 1000 + i * 2,
                    "high": 1005 + i * 2,
                    "low": 995 + i * 2,
                    "close": 1002 + i * 2,
                    "volume": 1000
                })
        self.df = pd.DataFrame(rows)

    def test_validate_strategy_with_auto_indicators(self):
        result = validate_strategy(self.df, train_ratio=0.7)
        self.assertIn("train_period", result)
        self.assertIn("test_period", result)
        self.assertIn("data_leakage_checks", result)
        self.assertFalse(result["data_leakage_checks"]["leakage_detected"])
        self.assertEqual(result["data_leakage_checks"]["status"], "PASS")

    def test_check_data_leakage_clean_data(self):
        train = self.df.iloc[:20]
        test = self.df.iloc[20:]
        # Note: self.df has alternating symbols or block symbols; let's split by timestamp
        t_split = self.df["timestamp"].unique()[10]
        train = self.df[self.df["timestamp"] < t_split]
        test = self.df[self.df["timestamp"] >= t_split]

        report = check_data_leakage(train, test)
        self.assertFalse(report["leakage_detected"])
        self.assertTrue(report["strict_chronological_order"])
        self.assertEqual(report["overlapping_timestamps_count"], 0)

    def test_check_data_leakage_detected_when_overlapping(self):
        train = self.df.iloc[:25]
        test = self.df.iloc[20:]  # 5 rows overlap!

        report = check_data_leakage(train, test)
        self.assertTrue(report["leakage_detected"])
        self.assertGreater(report["overlapping_timestamps_count"], 0)


if __name__ == "__main__":
    unittest.main()
