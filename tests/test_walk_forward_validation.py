
import unittest
import pandas as pd
from unittest.mock import patch

from src.backtesting.strategy_comparison import (
    split_walk_forward_windows,
    run_walk_forward_validation
)


class TestWalkForwardValidation(unittest.TestCase):

    def make_data(self):
        rows = []

        for day in range(30):
            rows.append({
                "timestamp": pd.Timestamp("2026-01-01")
                + pd.Timedelta(days=day),
                "symbol": "TEST",
                "open": 100 + day,
                "high": 102 + day,
                "low": 99 + day,
                "close": 101 + day,
                "volume": 1000
            })

        return pd.DataFrame(rows)

    def test_creates_multiple_folds(self):
        df = self.make_data()

        windows = split_walk_forward_windows(
            df,
            train_ratio=0.60,
            test_ratio=0.10
        )

        self.assertEqual(len(windows), 4)

    def test_training_window_expands(self):
        df = self.make_data()

        windows = split_walk_forward_windows(df)

        training_sizes = [
            window["training_timestamps"]
            for window in windows
        ]

        self.assertEqual(
            training_sizes,
            sorted(training_sizes)
        )

        self.assertEqual(training_sizes[0], 18)
        self.assertEqual(training_sizes[1], 21)

    def test_testing_windows_do_not_overlap(self):
        df = self.make_data()

        windows = split_walk_forward_windows(df)

        all_test_timestamps = []

        for window in windows:
            all_test_timestamps.extend(
                window["test"]["timestamp"].tolist()
            )

        self.assertEqual(
            len(all_test_timestamps),
            len(set(all_test_timestamps))
        )

    def test_training_data_precedes_testing_data(self):
        df = self.make_data()

        windows = split_walk_forward_windows(df)

        for window in windows:
            self.assertLess(
                window["train"]["timestamp"].max(),
                window["test"]["timestamp"].min()
            )

    def test_all_timestamps_are_tested_once(self):
        df = self.make_data()

        windows = split_walk_forward_windows(df)

        tested = []

        for window in windows:
            tested.extend(
                window["test"]["timestamp"].tolist()
            )

        expected = sorted(df["timestamp"].tolist())

        self.assertEqual(
            sorted(tested),
            expected[18:]
        )

    def test_invalid_ratios(self):
        df = self.make_data()

        with self.assertRaises(ValueError):
            split_walk_forward_windows(
                df,
                train_ratio=0,
                test_ratio=0.10
            )

        with self.assertRaises(ValueError):
            split_walk_forward_windows(
                df,
                train_ratio=0.80,
                test_ratio=0.30
            )

    def test_insufficient_data(self):
        df = self.make_data().head(2)

        with self.assertRaises(ValueError):
            split_walk_forward_windows(df)

    @patch(
        "src.backtesting.strategy_comparison.run_portfolio_backtest"
    )
    @patch(
        "src.backtesting.strategy_comparison.compare_ema_strategies"
    )
    def test_runs_walk_forward_validation(
        self,
        mock_compare,
        mock_backtest
    ):
        df = self.make_data()

        mock_compare.return_value = {
            "ranking": [
                {
                    "strategy": "EMA 5/20",
                    "fast_period": 5,
                    "slow_period": 20,
                    "net_pnl": 100,
                    "return_percent": 1,
                    "total_trades": 12,
                    "risk_adjusted_score": 0.5
                }
            ]
        }

        mock_backtest.return_value = {
            "net_pnl": 50,
            "return_percent": 0.5,
            "total_trades": 3,
            "max_drawdown_percent": 1.0
        }

        result = run_walk_forward_validation(df)

        self.assertEqual(result["total_folds"], 4)
        self.assertEqual(result["total_testing_trades"], 12)
        self.assertEqual(result["total_testing_net_pnl"], 200)
        self.assertEqual(result["profitable_folds"], 4)
        self.assertEqual(
            result["overall_sample_status"],
            "Sufficient sample"
        )

        self.assertEqual(mock_compare.call_count, 4)
        self.assertEqual(mock_backtest.call_count, 4)

    def test_rejects_reserved_backtest_parameters(self):
        df = self.make_data()

        with self.assertRaises(ValueError):
            run_walk_forward_validation(
                df,
                backtest_kwargs={
                    "fast_ema_period": 5
                }
            )


if __name__ == "__main__":
    unittest.main()
