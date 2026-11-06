
import unittest
from unittest.mock import patch

import pandas as pd

from src.backtesting.strategy_comparison import (
    prepare_strategy_data,
    compare_ema_strategies,
    calculate_risk_adjusted_score
)
from src.backtesting.strategy_comparison import (
    prepare_strategy_data,
    compare_ema_strategies,
    calculate_risk_adjusted_score,
    build_strategy_comparison_report,
    export_strategy_comparison_csv
)


class TestStrategyComparison(unittest.TestCase):

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
                    "timestamp": pd.Timestamp(
                        "2026-11-04 09:15"
                    ) + pd.Timedelta(minutes=5 * i),
                    "symbol": symbol,
                    "exchange": "NSE",
                    "open": price,
                    "high": price + 0.5,
                    "low": price - 0.5,
                    "close": price
                })

        return pd.DataFrame(rows)

    def test_prepare_strategy_data(self):

        df = self.make_data()

        result = prepare_strategy_data(
            df,
            fast_period=5,
            slow_period=20
        )

        self.assertIn("EMA_5", result.columns)
        self.assertIn("EMA_20", result.columns)

        self.assertEqual(len(result), len(df))

    def test_indicators_are_independent_by_symbol(self):

        df = self.make_data()

        result = prepare_strategy_data(
            df,
            fast_period=5,
            slow_period=20
        )

        aaa = result[result["symbol"] == "AAA"]
        bbb = result[result["symbol"] == "BBB"]

        pd.testing.assert_series_equal(
            aaa["EMA_5"].reset_index(drop=True),
            bbb["EMA_5"].reset_index(drop=True)
        )

    def test_invalid_strategy_periods(self):

        with self.assertRaises(ValueError):

            prepare_strategy_data(
                self.make_data(),
                fast_period=20,
                slow_period=5
            )

    def test_compare_multiple_strategies(self):

        df = self.make_data()

        configs = [
            {
                "name": "EMA 5/20",
                "fast_period": 5,
                "slow_period": 20
            },
            {
                "name": "EMA 9/21",
                "fast_period": 9,
                "slow_period": 21
            }
        ]

        result = compare_ema_strategies(
            df,
            strategy_configs=configs,
            backtest_kwargs={
                "initial_capital": 10000,
                "risk_per_trade": 100,
                "max_daily_loss": 500,
                "max_trades_per_day": 3
            }
        )

        self.assertEqual(result["total_strategies"], 2)
        self.assertEqual(len(result["ranking"]), 2)
        self.assertEqual(len(result["strategy_reports"]), 2)

        self.assertGreaterEqual(
            result["ranking"][0]["risk_adjusted_score"],
            result["ranking"][1]["risk_adjusted_score"]
        )

        self.assertIn(
            "sample_status",
            result["ranking"][0]
        )

    def test_duplicate_strategy_names(self):

        configs = [
            {
                "name": "EMA A",
                "fast_period": 5,
                "slow_period": 20
            },
            {
                "name": "EMA A",
                "fast_period": 9,
                "slow_period": 21
            }
        ]

        with self.assertRaises(ValueError):

            compare_ema_strategies(
                self.make_data(),
                strategy_configs=configs
            )

    # -----------------------------------
    # RISK-ADJUSTED SCORE TESTS
    # -----------------------------------

    def test_risk_adjusted_score_calculation(self):

        score = calculate_risk_adjusted_score(
            return_percent=12,
            max_drawdown_percent=8,
            total_trades=10
        )

        self.assertEqual(score, 1.3333)

    def test_zero_drawdown(self):

        score = calculate_risk_adjusted_score(
            return_percent=10,
            max_drawdown_percent=0,
            total_trades=10
        )

        self.assertEqual(score, 10.0)

    def test_insufficient_trade_count(self):

        score = calculate_risk_adjusted_score(
            return_percent=10,
            max_drawdown_percent=0,
            total_trades=5
        )

        self.assertEqual(score, 5.0)

    def test_no_trades(self):

        score = calculate_risk_adjusted_score(
            return_percent=0,
            max_drawdown_percent=0,
            total_trades=0
        )

        self.assertEqual(score, 0.0)

    def test_invalid_score_inputs(self):

        invalid_inputs = [
             (10, -1, 10),
            (10, 10, -1),
            (float("nan"), 10, 10),
            (10, float("inf"), 10),
            (10, 10, float("nan"))
        ]

        for return_pct, drawdown, trades in invalid_inputs:

            with self.subTest(
                return_pct=return_pct,
                drawdown=drawdown,
                trades=trades
            ):

                with self.assertRaises(ValueError):

                    calculate_risk_adjusted_score(
                        return_percent=return_pct,
                        max_drawdown_percent=drawdown,
                        total_trades=trades
                    )

    @patch(
        "src.backtesting.strategy_comparison.run_portfolio_backtest"
    )
    def test_ranking_uses_risk_adjusted_score(self, mock_backtest):

        mock_backtest.side_effect = [
            {
                "net_pnl": 1200,
                "return_percent": 12,
                "total_trades": 10,
                "win_rate": 60,
                "profit_factor": 1.8,
                "max_drawdown_percent": 8,
                "total_costs": 100
            },
            {
                "net_pnl": 1000,
                "return_percent": 10,
                "total_trades": 10,
                "win_rate": 65,
                "profit_factor": 2.0,
                "max_drawdown_percent": 3,
                "total_costs": 80
            }
        ]

        configs = [
            {
                "name": "Higher Profit",
                "fast_period": 5,
                "slow_period": 20
            },
            {
                "name": "Lower Drawdown",
                "fast_period": 9,
                "slow_period": 21
            }
        ]

        result = compare_ema_strategies(
            self.make_data(),
            strategy_configs=configs
        )

        self.assertEqual(
            result["ranking"][0]["strategy"],
            "Lower Drawdown"
        )

        self.assertEqual(
            result["ranking"][0]["rank"],
            1
        )

        self.assertGreater(
            result["ranking"][0]["risk_adjusted_score"],
            result["ranking"][1]["risk_adjusted_score"]
        )


if __name__ == "__main__":
    unittest.main()

    # -----------------------------------
    # REPORTING AND CSV EXPORT TESTS
    # -----------------------------------

    def make_comparison_result(self):

        ranking = [
            {
                "strategy": "EMA 9/21",
                "net_pnl": 1000,
                "return_percent": 10,
                "max_drawdown_percent": 3,
                "risk_adjusted_score": 2.5,
                "total_trades": 15,
                "sample_status": "Sufficient sample"
            },
            {
                "strategy": "EMA 5/20",
                "net_pnl": 1500,
                "return_percent": 15,
                "max_drawdown_percent": 10,
                "risk_adjusted_score": 1.36,
                "total_trades": 20,
                "sample_status": "Sufficient sample"
            },
            {
                "strategy": "EMA 20/50",
                "net_pnl": 300,
                "return_percent": 3,
                "max_drawdown_percent": 2,
                "risk_adjusted_score": 0.3,
                "total_trades": 3,
                "sample_status": "Insufficient sample"
            }
        ]

        return {
            "total_strategies": 3,
            "ranking": ranking,
            "strategy_reports": {}
        }

    def test_best_risk_adjusted_strategy(self):

        report = build_strategy_comparison_report(
            self.make_comparison_result()
        )

        self.assertEqual(
            report["best_risk_adjusted"]["strategy"],
            "EMA 9/21"
        )

    def test_highest_profit_strategy(self):

        report = build_strategy_comparison_report(
            self.make_comparison_result()
        )

        self.assertEqual(
            report["highest_net_profit"]["strategy"],
            "EMA 5/20"
        )

    def test_lowest_drawdown_strategy(self):

        report = build_strategy_comparison_report(
            self.make_comparison_result()
        )

        self.assertEqual(
            report["lowest_drawdown"]["strategy"],
            "EMA 20/50"
        )

    def test_insufficient_sample_warning(self):

        report = build_strategy_comparison_report(
            self.make_comparison_result()
        )

        self.assertEqual(
            report["insufficient_sample_strategies"],
            ["EMA 20/50"]
        )

    def test_export_strategy_comparison_csv(self):

        import tempfile
        from pathlib import Path

        comparison_result = self.make_comparison_result()

        with tempfile.TemporaryDirectory() as temp_dir:

            output_path = Path(temp_dir) / "reports" / "comparison.csv"

            result_path = export_strategy_comparison_csv(
                comparison_result,
                output_path=output_path
            )

            self.assertTrue(Path(result_path).exists())

            exported_df = pd.read_csv(result_path)

            self.assertEqual(len(exported_df), 3)

            self.assertIn(
                "risk_adjusted_score",
                exported_df.columns
            )

            self.assertEqual(
                exported_df.iloc[0]["strategy"],
                "EMA 9/21"
            )

    def test_invalid_comparison_report(self):

        invalid_results = [
            None,
            {},
            {"ranking": []},
            {"ranking": [{"strategy": "EMA 9/21"}]}
        ]

        for result in invalid_results:

            with self.subTest(result=result):

                with self.assertRaises(ValueError):

                    build_strategy_comparison_report(result)