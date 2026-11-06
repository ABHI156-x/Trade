
import unittest

from src.backtesting.strategy_selector import (
    select_strategy_for_regime
)


class TestStrategySelector(unittest.TestCase):

    def make_result(self):
        return {
            "regime_rankings": {
                "TRENDING_UP": [
                    {
                        "strategy": "EMA 5/20",
                        "total_trades": 20,
                        "net_pnl": 500,
                        "max_drawdown_percent": 2.0,
                        "risk_adjusted_score": 4.5
                    },
                    {
                        "strategy": "EMA 9/21",
                        "total_trades": 15,
                        "net_pnl": 300,
                        "max_drawdown_percent": 1.5,
                        "risk_adjusted_score": 3.2
                    }
                ],
                "SIDEWAYS": [
                    {
                        "strategy": "EMA 12/26",
                        "total_trades": 5,
                        "net_pnl": 100,
                        "max_drawdown_percent": 1.0,
                        "risk_adjusted_score": 1.0
                    }
                ]
            }
        }

    def valid_validation(self):
        return {
            "EMA 5/20": {
                "passed": True,
                "reasons": []
            },
            "EMA 9/21": {
                "passed": True,
                "reasons": []
            }
        }

    def test_selects_best_strategy_after_validation(self):
        result = select_strategy_for_regime(
            self.make_result(),
            "TRENDING_UP",
            validation_results=self.valid_validation()
        )

        self.assertEqual(result["status"], "SELECTED")
        self.assertEqual(
            result["selected_strategy"]["strategy"],
            "EMA 5/20"
        )

    def test_does_not_select_without_validation(self):
        result = select_strategy_for_regime(
            self.make_result(),
            "TRENDING_UP"
        )

        self.assertEqual(result["status"], "NO_TRADE")
        self.assertIsNone(result["selected_strategy"])
        self.assertEqual(
            result["top_candidate"]["strategy"],
            "EMA 5/20"
        )

    def test_rejects_insufficient_trade_sample(self):
        result = select_strategy_for_regime(
            self.make_result(),
            "SIDEWAYS",
            validation_results={
                "EMA 12/26": {
                    "passed": True,
                    "reasons": []
                }
            }
        )

        self.assertEqual(result["status"], "NO_TRADE")
        self.assertIsNone(result["selected_strategy"])

    def test_rejects_negative_net_pnl(self):
        data = self.make_result()
        data["regime_rankings"]["TRENDING_UP"][0]["net_pnl"] = -100
        data["regime_rankings"]["TRENDING_UP"][1]["net_pnl"] = -50

        result = select_strategy_for_regime(
            data,
            "TRENDING_UP",
            validation_results=self.valid_validation()
        )

        self.assertEqual(result["status"], "NO_TRADE")

    def test_rejects_excessive_drawdown(self):
        data = self.make_result()
        data["regime_rankings"]["TRENDING_UP"][0][
            "max_drawdown_percent"
        ] = 8.0

        result = select_strategy_for_regime(
            data,
            "TRENDING_UP",
            max_drawdown_percent=5.0,
            validation_results=self.valid_validation()
        )

        # EMA 5/20 is rejected, but EMA 9/21 remains eligible.
        self.assertEqual(result["status"], "SELECTED")
        self.assertEqual(
            result["selected_strategy"]["strategy"],
            "EMA 9/21"
        )

    def test_rejects_non_positive_score(self):
        data = self.make_result()
        data["regime_rankings"]["TRENDING_UP"][0][
            "risk_adjusted_score"
        ] = 0
        data["regime_rankings"]["TRENDING_UP"][1][
            "risk_adjusted_score"
        ] = -1

        result = select_strategy_for_regime(
            data,
            "TRENDING_UP",
            validation_results=self.valid_validation()
        )

        self.assertEqual(result["status"], "NO_TRADE")

    def test_unknown_regime_returns_no_trade(self):
        result = select_strategy_for_regime(
            self.make_result(),
            "HIGH_VOLATILITY"
        )

        self.assertEqual(result["status"], "NO_TRADE")
        self.assertIsNone(result["selected_strategy"])

    def test_empty_regime_ranking_returns_no_trade(self):
        data = {
            "regime_rankings": {
                "SIDEWAYS": []
            }
        }

        result = select_strategy_for_regime(
            data,
            "SIDEWAYS"
        )

        self.assertEqual(result["status"], "NO_TRADE")

    def test_invalid_minimum_trades(self):
        with self.assertRaises(ValueError):
            select_strategy_for_regime(
                self.make_result(),
                "TRENDING_UP",
                minimum_trades=0
            )

    def test_invalid_drawdown_limit(self):
        with self.assertRaises(ValueError):
            select_strategy_for_regime(
                self.make_result(),
                "TRENDING_UP",
                max_drawdown_percent=-1
            )

    def test_rejects_invalid_candidate_metrics(self):
        data = self.make_result()
        data["regime_rankings"]["TRENDING_UP"][0][
            "risk_adjusted_score"
        ] = float("nan")

        with self.assertRaises(ValueError):
            select_strategy_for_regime(
                data,
                "TRENDING_UP"
            )

    def test_rejects_invalid_validation_flag(self):
        with self.assertRaises(ValueError):
            select_strategy_for_regime(
                self.make_result(),
                "TRENDING_UP",
                validation_results="yes"
            )


if __name__ == "__main__":
    unittest.main()
