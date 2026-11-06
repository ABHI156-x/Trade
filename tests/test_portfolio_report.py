
import unittest

from src.backtesting.portfolio_report import (
    build_portfolio_summary,
    get_symbol_performance,
    get_daily_performance,
    get_trade_history,
    calculate_trade_metrics
)


class TestPortfolioReport(unittest.TestCase):

    def setUp(self):

        self.report = {
            "initial_capital": 10000,
            "final_capital": 10150,
            "net_pnl": 150,
            "total_costs": 20,
            "total_trades": 3,
            "winning_trades": 2,
            "losing_trades": 1,
            "win_rate": 66.67,
            "profit_factor": 2.5,
            "max_drawdown_percent": 1.5,
            "blocked_entries": 1,

            "trade_history": [
                {
                    "symbol": "RELIANCE",
                    "entry_time": "2026-11-04 09:20",
                    "exit_time": "2026-11-04 09:30",
                    "entry": 100,
                    "exit": 110,
                    "quantity": 10,
                    "reason": "TARGET",
                    "gross_pnl": 100,
                    "total_cost": 10,
                    "net_pnl": 90
                },
                {
                    "symbol": "TCS",
                    "entry_time": "2026-11-04 09:20",
                    "exit_time": "2026-11-04 09:30",
                    "entry": 100,
                    "exit": 95,
                    "quantity": 10,
                    "reason": "STOP_LOSS",
                    "gross_pnl": -50,
                    "total_cost": 5,
                    "net_pnl": -55
                },
                {
                    "symbol": "RELIANCE",
                    "entry_time": "2026-11-05 09:20",
                    "exit_time": "2026-11-05 09:30",
                    "entry": 100,
                    "exit": 112,
                    "quantity": 10,
                    "reason": "TARGET",
                    "gross_pnl": 120,
                    "total_cost": 5,
                    "net_pnl": 115
                }
            ],

            "equity_history": [
                {"timestamp": None, "equity": 10000},
                {"timestamp": "2026-11-04 09:20", "equity": 10000},
                {"timestamp": "2026-11-04 09:30", "equity": 10035},
                {"timestamp": "2026-11-05 09:20", "equity": 10035},
                {"timestamp": "2026-11-05 09:30", "equity": 10150}
            ]
        }

    # Existing tests

    def test_portfolio_summary(self):
        result = build_portfolio_summary(self.report)

        self.assertEqual(result["net_pnl"], 150)
        self.assertEqual(result["total_trades"], 3)

    def test_symbol_performance(self):
        result = get_symbol_performance(self.report)

        reliance = result[
            result["symbol"] == "RELIANCE"
        ].iloc[0]

        self.assertEqual(reliance["trades"], 2)
        self.assertEqual(reliance["winning_trades"], 2)
        self.assertEqual(reliance["net_pnl"], 205)

    def test_daily_performance(self):
        result = get_daily_performance(self.report)

        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]["daily_pnl"], 35)
        self.assertEqual(result.iloc[1]["daily_pnl"], 115)

    def test_trade_history(self):
        result = get_trade_history(self.report)

        self.assertEqual(len(result), 3)
        self.assertIn("net_pnl", result.columns)

    def test_average_win_and_loss(self):
        result = calculate_trade_metrics(
            self.report["trade_history"]
        )

        self.assertEqual(result["average_win"], 102.5)
        self.assertEqual(result["average_loss"], 55)

    def test_expectancy(self):
        result = calculate_trade_metrics(
            self.report["trade_history"]
        )

        self.assertEqual(result["expectancy"], 50)

    def test_risk_reward_ratio(self):
        result = calculate_trade_metrics(
            self.report["trade_history"]
        )

        self.assertEqual(result["risk_reward_ratio"], 1.86)

    def test_breakeven_trade(self):
        trades = [
            {"net_pnl": 100},
            {"net_pnl": -50},
            {"net_pnl": 0}
        ]

        result = calculate_trade_metrics(trades)

        self.assertEqual(result["breakeven_trades"], 1)

    def test_empty_trade_metrics(self):
        result = calculate_trade_metrics([])

        self.assertEqual(result["expectancy"], 0)
        self.assertIsNone(result["risk_reward_ratio"])
        self.assertEqual(result["breakeven_trades"], 0)

    def test_summary_has_advanced_metrics(self):
        result = build_portfolio_summary(self.report)

        self.assertIn("average_win", result)
        self.assertIn("average_loss", result)
        self.assertIn("expectancy", result)
        self.assertIn("risk_reward_ratio", result)
        self.assertIn("net_profit_factor", result)

    # New Batch 5 tests

    def test_profit_factor_without_losing_trades(self):
        trades = [
            {"net_pnl": 100},
            {"net_pnl": 200},
            {"net_pnl": 50}
        ]

        result = calculate_trade_metrics(trades)

        self.assertIsNone(result["net_profit_factor"])

    def test_expectancy_with_wins_losses_and_breakeven(self):
        trades = [
            {"net_pnl": 100},
            {"net_pnl": -50},
            {"net_pnl": 0},
            {"net_pnl": 150}
        ]

        result = calculate_trade_metrics(trades)

        # (100 - 50 + 0 + 150) / 4 = 50
        self.assertEqual(result["expectancy"], 50)
        self.assertEqual(result["breakeven_trades"], 1)

    def test_empty_portfolio_report(self):
        empty_report = {
            "initial_capital": 10000,
            "final_capital": 10000,
            "net_pnl": 0,
            "total_costs": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "trade_history": [],
            "equity_history": []
        }

        summary = build_portfolio_summary(empty_report)
        symbols = get_symbol_performance(empty_report)
        daily = get_daily_performance(empty_report)
        history = get_trade_history(empty_report)

        self.assertEqual(summary["net_pnl"], 0)
        self.assertEqual(summary["total_trades"], 0)
        self.assertTrue(symbols.empty)
        self.assertTrue(daily.empty)
        self.assertTrue(history.empty)

    def test_symbol_performance_sorted_by_net_pnl(self):
        result = get_symbol_performance(self.report)

        self.assertGreaterEqual(
            result.iloc[0]["net_pnl"],
            result.iloc[-1]["net_pnl"]
        )

    def test_daily_pnl_matches_total_equity_change(self):
        result = get_daily_performance(self.report)

        total_daily_pnl = result["daily_pnl"].sum()

        expected_pnl = (
            self.report["final_capital"]
            - self.report["initial_capital"]
        )

        self.assertAlmostEqual(total_daily_pnl, expected_pnl)


if __name__ == "__main__":
    unittest.main()
