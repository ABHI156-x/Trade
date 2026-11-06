
import unittest
from unittest.mock import patch

from src.backtesting.strategy_comparison import (
    analyze_ema_parameter_sensitivity
)


class TestParameterSensitivity(unittest.TestCase):

    def make_ranking(self, profitable_count=20):
        ranking = []

        for fast in range(7, 12):
            for slow in range(19, 24):
                if fast >= slow:
                    continue

                pnl = 100 if len(ranking) < profitable_count else -50

                ranking.append({
                    "strategy": f"EMA {fast}/{slow}",
                    "fast_period": fast,
                    "slow_period": slow,
                    "net_pnl": pnl,
                    "return_percent": pnl / 100,
                    "total_trades": 12,
                    "max_drawdown_percent": 2,
                    "risk_adjusted_score": 0.5
                })

        # Ensure baseline EMA 9/21 is profitable.
        for item in ranking:
            if item["fast_period"] == 9 and item["slow_period"] == 21:
                item["net_pnl"] = 100

        return ranking

    @patch(
        "src.backtesting.strategy_comparison.compare_ema_strategies"
    )
    def test_default_combinations(self, mock_compare):
        mock_compare.return_value = {
            "ranking": self.make_ranking()
        }

        result = analyze_ema_parameter_sensitivity(
            df=object()
        )

        self.assertEqual(result["total_combinations"], 25)
        mock_compare.assert_called_once()

    @patch(
        "src.backtesting.strategy_comparison.compare_ema_strategies"
    )
    def test_baseline_strategy_is_identified(self, mock_compare):
        mock_compare.return_value = {
            "ranking": self.make_ranking()
        }

        result = analyze_ema_parameter_sensitivity(
            df=object()
        )

        self.assertEqual(
            result["baseline_strategy"]["fast_period"],
            9
        )

        self.assertEqual(
            result["baseline_strategy"]["slow_period"],
            21
        )

    @patch(
        "src.backtesting.strategy_comparison.compare_ema_strategies"
    )
    def test_robustness_status_is_relatively_stable(self, mock_compare):
        mock_compare.return_value = {
            "ranking": self.make_ranking(20)
        }

        result = analyze_ema_parameter_sensitivity(
            df=object()
        )

        self.assertEqual(
            result["robustness_status"],
            "Relatively stable"
        )

    @patch(
        "src.backtesting.strategy_comparison.compare_ema_strategies"
    )
    def test_robustness_status_is_moderately_sensitive(self, mock_compare):
        mock_compare.return_value = {
            "ranking": self.make_ranking(10)
        }

        result = analyze_ema_parameter_sensitivity(
            df=object()
        )

        self.assertEqual(
            result["robustness_status"],
            "Moderately sensitive"
        )

    @patch(
        "src.backtesting.strategy_comparison.compare_ema_strategies"
    )
    def test_robustness_status_is_highly_sensitive(self, mock_compare):
        mock_compare.return_value = {
            "ranking": self.make_ranking(5)
        }

        result = analyze_ema_parameter_sensitivity(
            df=object()
        )

        self.assertEqual(
            result["robustness_status"],
            "Highly sensitive"
        )

    def test_rejects_invalid_periods(self):
        with self.assertRaises(ValueError):
            analyze_ema_parameter_sensitivity(
                df=object(),
                fast_periods=[7, 0, 9]
            )

    def test_rejects_duplicate_periods(self):
        with self.assertRaises(ValueError):
            analyze_ema_parameter_sensitivity(
                df=object(),
                fast_periods=[7, 7, 9]
            )

    def test_rejects_missing_baseline(self):
        with self.assertRaises(ValueError):
            analyze_ema_parameter_sensitivity(
                df=object(),
                fast_periods=[5, 6],
                slow_periods=[15, 16],
                baseline_fast=9,
                baseline_slow=21
            )


if __name__ == "__main__":
    unittest.main()
