
import unittest
import pandas as pd

from src.market_data.data_quality import (
    check_market_data_quality
)


class TestDataQuality(unittest.TestCase):

    def setUp(self):

        self.df = pd.DataFrame([
            {
                "timestamp": "2026-11-04 09:15",
                "symbol": "RELIANCE",
                "open": 100,
                "high": 105,
                "low": 99,
                "close": 103,
                "volume": 1000
            },
            {
                "timestamp": "2026-11-04 09:20",
                "symbol": "RELIANCE",
                "open": 103,
                "high": 108,
                "low": 102,
                "close": 107,
                "volume": 1200
            }
        ])

    def test_clean_data(self):

        result = check_market_data_quality(self.df)

        self.assertEqual(result["issue_count"], 0)

    def test_duplicate_timestamp(self):

        duplicate = pd.concat(
            [self.df, self.df.iloc[[0]]],
            ignore_index=True
        )

        result = check_market_data_quality(duplicate)

        self.assertGreater(result["issue_count"], 0)

        self.assertTrue(
            any(
                issue["issue"] == "DUPLICATE_TIMESTAMP"
                for issue in result["issues"]
            )
        )

    def test_missing_candle(self):

        incomplete = self.df.iloc[[0]].copy()

        incomplete.loc[len(incomplete)] = {
            "timestamp": "2026-11-04 09:25",
            "symbol": "RELIANCE",
            "open": 103,
            "high": 108,
            "low": 102,
            "close": 107,
            "volume": 1200
        }

        result = check_market_data_quality(incomplete)

        self.assertTrue(
            any(
                issue["issue"] == "MISSING_CANDLE"
                for issue in result["issues"]
            )
        )

    def test_invalid_ohlc(self):

        invalid = self.df.copy()
        invalid.loc[0, "high"] = 95

        result = check_market_data_quality(invalid)

        self.assertTrue(
            any(
                issue["issue"] == "INVALID_OHLC"
                for issue in result["issues"]
            )
        )

    def test_negative_volume(self):

        invalid = self.df.copy()
        invalid.loc[0, "volume"] = -100

        result = check_market_data_quality(invalid)

        self.assertTrue(
            any(
                issue["issue"] == "NEGATIVE_VOLUME"
                for issue in result["issues"]
            )
        )

    def test_empty_data(self):

        result = check_market_data_quality(
            self.df.iloc[0:0]
        )

        self.assertEqual(result["total_rows"], 0)
        self.assertEqual(result["issue_count"], 0)


if __name__ == "__main__":
    unittest.main()
