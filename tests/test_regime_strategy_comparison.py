
import unittest
from unittest.mock import patch

import pandas as pd

from src.backtesting.regime_strategy_comparison import (
    compare_strategies_by_market_regime
)


class TestRegimeStrategyComparison(unittest.TestCase):

    def make_data(self):
        return pd.DataFrame({
            "timestamp": pd.to_datetime([
                "2026-01-01 10:00:00",
                "2026-01-02 10:00:00"
            ]),
            "symbol": ["AAA", "AAA"],
            "open": [100, 101],
            "high": [102, 103],
            "low": [99, 100],
            "close": [101, 102],
            "volume": [1000, 1200]
        })

    def make_classified_data(self):
        df = self.make_data()

        df["MARKET_REGIME"] = [
            "TRENDING_UP",
            "SIDEWAYS"
        ]

        return df

    def make_trade(
        self,
        entry_time,
        exit_time,
        pnl,
        cost=5
    ):
        return {
            "symbol": "AAA",
            "entry_time": entry_time,
            "exit_time": exit_time,
            "entry": 100,
            "quantity": 10,
            "net_pnl": pnl,
            "total_cost": cost
        }

    def make_comparison_result(self):
        strategy_one = {
            "strategy": "EMA 5/20",
            "fast_period": 5,
            "slow_period": 20,
            "report": {
                "trade_history": [
                    self.make_trade(
                        "2026-01-01 10:00:00",
                        "2026-01-01 10:30:00",
                        100
                    ),
                    self.make_trade(
                        "2026-01-02 10:00:00",
                        "2026-01-02 10:30:00",
                        -50
                    )
                ]
            }
        }

        strategy_two = {
            "strategy": "EMA 9/21",
            "fast_period": 9,
            "slow_period": 21,
            "report": {
                "trade_history": [
                    self.make_trade(
                        "2026-01-01 10:00:00",
                        "2026-01-01 10:30:00",
                        50
                    ),
                    self.make_trade(
                        "2026-01-02 10:00:00",
                        "2026-01-02 10:30:00",
                        80
                    )
                ]
            }
        }

        return {
            "total_strategies": 2,
            "strategy_reports": [
                strategy_one,
                strategy_two
            ]
        }

    def run_analysis(self, df=None, comparison=None):
        if df is None:
            df = self.make_data()

        if comparison is None:
            comparison = self.make_comparison_result()

        with patch(
            "src.backtesting.regime_strategy_comparison."
            "classify_regimes_by_symbol",
            return_value=self.make_classified_data()
        ), patch(
            "src.backtesting.regime_strategy_comparison."
            "compare_ema_strategies",
            return_value=comparison
        ):
            return compare_strategies_by_market_regime(df)

    def test_compares_strategies_by_regime(self):
        result = self.run_analysis()

        self.assertEqual(
            result["total_strategies"],
            2
        )

        self.assertIn(
            "TRENDING_UP",
            result["regime_rankings"]
        )

        self.assertIn(
            "SIDEWAYS",
            result["regime_rankings"]
        )

    def test_identifies_best_strategy_in_each_regime(self):
        result = self.run_analysis()

        self.assertEqual(
            result["best_strategy_by_regime"]["TRENDING_UP"]["strategy"],
            "EMA 5/20"
        )

        self.assertEqual(
            result["best_strategy_by_regime"]["SIDEWAYS"]["strategy"],
            "EMA 9/21"
        )

    def test_calculates_regime_net_pnl(self):
        result = self.run_analysis()

        trending = result["regime_rankings"]["TRENDING_UP"]
        sideways = result["regime_rankings"]["SIDEWAYS"]

        self.assertEqual(
            trending[0]["net_pnl"],
            100
        )

        self.assertEqual(
            sideways[0]["net_pnl"],
            80
        )

    def test_calculates_win_rate_and_costs(self):
        result = self.run_analysis()

        trending = result["regime_rankings"]["TRENDING_UP"][0]

        self.assertEqual(trending["win_rate"], 100)
        self.assertEqual(trending["total_costs"], 5)
        self.assertEqual(trending["total_trades"], 1)

    def test_includes_unknown_regime(self):
        result = self.run_analysis()

        self.assertIn(
            "UNKNOWN",
            result["regime_rankings"]
        )

        self.assertIsNone(
            result["best_strategy_by_regime"]["UNKNOWN"]
        )

    def test_marks_small_samples_as_insufficient(self):
        result = self.run_analysis()

        for regime in ("TRENDING_UP", "SIDEWAYS"):
            for item in result["regime_rankings"][regime]:
                self.assertEqual(
                    item["sample_status"],
                    "Insufficient sample"
                )

    def test_rejects_duplicate_market_candles(self):
        df = self.make_data()

        df = pd.concat(
            [df, df.iloc[[0]]],
            ignore_index=True
        )

        with self.assertRaises(ValueError):
            compare_strategies_by_market_regime(df)

    def test_rejects_invalid_trade_data(self):
        comparison = self.make_comparison_result()

        comparison["strategy_reports"][0]["report"][
            "trade_history"
        ][0]["net_pnl"] = float("nan")

        with self.assertRaises(ValueError):
            self.run_analysis(comparison=comparison)


if __name__ == "__main__":
    unittest.main()
