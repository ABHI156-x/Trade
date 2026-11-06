import unittest
from unittest.mock import patch

import pandas as pd

from src.backtesting.strategy_comparison import (
    split_market_data,
    run_out_of_sample_validation
)


class TestOutOfSampleValidation(unittest.TestCase):

    def make_data(self):

        rows = []

        prices = [
            100, 101, 102, 103, 104,
            105, 106, 107, 108, 109,
            110, 109, 108, 107, 106,
            105, 104, 103, 102, 101,
            100, 101, 102, 103, 104,
            105, 106, 107, 108, 109
        ]

        for symbol in ["AAA", "BBB"]:

            for i, price in enumerate(prices):

                rows.append({
                    "timestamp": (
                        pd.Timestamp("2026-11-04 09:15")
                        + pd.Timedelta(minutes=5 * i)
                    ),
                    "symbol": symbol,
                    "exchange": "NSE",
                    "open": price,
                    "high": price + 0.5,
                    "low": price - 0.5,
                    "close": price
                })

        return pd.DataFrame(rows)

    def test_chronological_split(self):

        result = split_market_data(
            self.make_data(),
            train_ratio=0.70
        )

        train_df = result["train"]
        test_df = result["test"]

        self.assertLess(
            train_df["timestamp"].max(),
            test_df["timestamp"].min()
        )

    def test_split_keeps_symbols_together(self):

        result = split_market_data(self.make_data())

        train_df = result["train"]
        test_df = result["test"]

        for timestamp, group in train_df.groupby("timestamp"):
            self.assertEqual(len(group), 2)

        for timestamp, group in test_df.groupby("timestamp"):
            self.assertEqual(len(group), 2)

    def test_split_ratio(self):

        result = split_market_data(
            self.make_data(),
            train_ratio=0.70
        )

        self.assertEqual(
            result["training_timestamps"],
            21
        )

        self.assertEqual(
            result["testing_timestamps"],
            9
        )

    def test_invalid_train_ratio(self):

        invalid_ratios = [
            0,
            1,
            -0.5,
            1.5,
            float("nan"),
            float("inf"),
            True
        ]

        for ratio in invalid_ratios:

            with self.subTest(ratio=ratio):

                with self.assertRaises(ValueError):
                    split_market_data(
                        self.make_data(),
                        train_ratio=ratio
                    )

    def test_single_timestamp_rejected(self):

        df = self.make_data()

        df = df[
            df["timestamp"] == df["timestamp"].min()
        ]

        with self.assertRaises(ValueError):
            split_market_data(df)

    @patch(
        "src.backtesting.strategy_comparison.run_portfolio_backtest"
    )
    def test_out_of_sample_validation(self, mock_backtest):

        mock_backtest.side_effect = [
            {
                "net_pnl": 1000,
                "return_percent": 10,
                "total_trades": 15,
                "win_rate": 60,
                "profit_factor": 1.8,
                "max_drawdown_percent": 3,
                "total_costs": 100
            },
            {
                "net_pnl": 200,
                "return_percent": 2,
                "total_trades": 5,
                "win_rate": 60,
                "profit_factor": 1.5,
                "max_drawdown_percent": 2,
                "total_costs": 50
            }
        ]

        configs = [
            {
                "name": "EMA 5/20",
                "fast_period": 5,
                "slow_period": 20
            }
        ]

        result = run_out_of_sample_validation(
            self.make_data(),
            strategy_configs=configs
        )

        self.assertEqual(
            result["selected_strategy"]["strategy"],
            "EMA 5/20"
        )

        self.assertEqual(
            result["testing_report"]["net_pnl"],
            200
        )

        self.assertEqual(
            result["testing_sample_status"],
            "Insufficient sample"
        )

        self.assertEqual(
            mock_backtest.call_count,
            2
        )

    def test_original_dataframe_not_modified(self):

        df = self.make_data()
        original = df.copy(deep=True)

        # The split function must not modify the input.
        split_market_data(df)

        pd.testing.assert_frame_equal(df, original)


if __name__ == "__main__":
    unittest.main()