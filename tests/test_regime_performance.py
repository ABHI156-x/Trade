
import unittest
import pandas as pd

from src.backtesting.regime_performance import (
    analyze_regime_performance
)


class TestRegimePerformance(unittest.TestCase):

    def make_report(self):
        return {
            "trade_history": [
                {
                    "symbol": "AAA",
                    "entry_time": "2026-01-01 10:00:00",
                    "net_pnl": 100,
                    "total_cost": 10,
                    "entry": 100,
                    "quantity": 10
                },
                {
                    "symbol": "AAA",
                    "entry_time": "2026-01-02 10:00:00",
                    "net_pnl": -50,
                    "total_cost": 8,
                    "entry": 100,
                    "quantity": 10
                },
                {
                    "symbol": "BBB",
                    "entry_time": "2026-01-03 10:00:00",
                    "net_pnl": 0,
                    "total_cost": 5,
                    "entry": 200,
                    "quantity": 5
                }
            ]
        }

    def make_regimes(self):
        return pd.DataFrame({
            "timestamp": pd.to_datetime([
                "2026-01-01 10:00:00",
                "2026-01-02 10:00:00",
                "2026-01-03 10:00:00"
            ]),
            "symbol": ["AAA", "AAA", "BBB"],
            "MARKET_REGIME": [
                "TRENDING_UP",
                "SIDEWAYS",
                "HIGH_VOLATILITY"
            ]
        })

    def test_groups_trades_by_regime(self):
        result = analyze_regime_performance(
            self.make_report(),
            self.make_regimes()
        )

        self.assertEqual(
            result["total_trades_analyzed"],
            3
        )

        self.assertEqual(
            len(result["regime_performance"]),
            4
        )

    def test_calculates_net_pnl(self):
        result = analyze_regime_performance(
            self.make_report(),
            self.make_regimes()
        )

        performance = {
            item["market_regime"]: item
            for item in result["regime_performance"]
        }

        self.assertEqual(
            performance["TRENDING_UP"]["net_pnl"],
            100
        )

        self.assertEqual(
            performance["SIDEWAYS"]["net_pnl"],
            -50
        )

    def test_calculates_win_rate(self):
        result = analyze_regime_performance(
            self.make_report(),
            self.make_regimes()
        )

        performance = {
            item["market_regime"]: item
            for item in result["regime_performance"]
        }

        self.assertEqual(
            performance["TRENDING_UP"]["win_rate"],
            100
        )

        self.assertEqual(
            performance["SIDEWAYS"]["win_rate"],
            0
        )

    def test_calculates_breakeven_trades(self):
        result = analyze_regime_performance(
            self.make_report(),
            self.make_regimes()
        )

        performance = {
            item["market_regime"]: item
            for item in result["regime_performance"]
        }

        self.assertEqual(
            performance["HIGH_VOLATILITY"]["breakeven_trades"],
            1
        )

    def test_identifies_best_and_worst_regime(self):
        result = analyze_regime_performance(
            self.make_report(),
            self.make_regimes()
        )

        self.assertEqual(
            result["best_regime"]["market_regime"],
            "TRENDING_UP"
        )

        self.assertEqual(
            result["worst_regime"]["market_regime"],
            "SIDEWAYS"
        )

    def test_unmatched_trade_is_unknown(self):
        report = self.make_report()
        report["trade_history"][0]["entry_time"] = (
            "2026-01-10 10:00:00"
        )

        result = analyze_regime_performance(
            report,
            self.make_regimes()
        )

        self.assertEqual(result["unmatched_trades"], 1)

    def test_rejects_duplicate_regime_data(self):
        regimes = self.make_regimes()
        regimes = pd.concat(
            [regimes, regimes.iloc[[0]]],
            ignore_index=True
        )

        with self.assertRaises(ValueError):
            analyze_regime_performance(
                self.make_report(),
                regimes
            )

    def test_rejects_invalid_report(self):
        with self.assertRaises(ValueError):
            analyze_regime_performance(
                {},
                self.make_regimes()
            )


if __name__ == "__main__":
    unittest.main()
