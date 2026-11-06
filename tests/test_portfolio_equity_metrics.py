
import unittest
import pandas as pd

from src.backtesting.portfolio_backtester import (
    run_portfolio_backtest
)


class TestPortfolioEquityMetrics(unittest.TestCase):

    def make_data(self):

        return pd.DataFrame([
            {
                "timestamp": "2026-11-04 09:15",
                "symbol": "TEST",
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "EMA_9": 9,
                "EMA_21": 10
            },
            {
                "timestamp": "2026-11-04 09:20",
                "symbol": "TEST",
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "EMA_9": 11,
                "EMA_21": 10
            }
        ])

    def test_final_equity_matches_final_capital(self):

        result = run_portfolio_backtest(
            self.make_data()
        )

        self.assertAlmostEqual(
            result["equity_curve"][-1],
            result["final_capital"]
        )

    def test_end_of_data_close_is_recorded(self):

        result = run_portfolio_backtest(
            self.make_data()
        )

        last_record = result["equity_history"][-1]

        self.assertAlmostEqual(
            last_record["equity"],
            result["final_capital"]
        )

        self.assertAlmostEqual(
            last_record["balance"],
            result["final_capital"]
        )

        self.assertEqual(
            last_record["unrealized_pnl"],
            0.0
        )

    def test_drawdown_metrics_are_non_negative(self):

        result = run_portfolio_backtest(
            self.make_data()
        )

        self.assertGreaterEqual(
            result["max_drawdown_amount"],
            0
        )

        self.assertGreaterEqual(
            result["max_drawdown_percent"],
            0
        )

    def test_return_percentage(self):

        result = run_portfolio_backtest(
            self.make_data()
        )

        expected = (
            result["net_pnl"]
            / result["initial_capital"]
        ) * 100

        self.assertAlmostEqual(
            result["return_percent"],
            round(expected, 2)
        )

    def test_no_remaining_positions(self):

        result = run_portfolio_backtest(
            self.make_data()
        )

        self.assertEqual(
            result["remaining_positions"],
            0
        )


if __name__ == "__main__":
    unittest.main()
