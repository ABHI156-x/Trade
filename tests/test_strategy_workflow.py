import unittest
from unittest.mock import patch

import pandas as pd

from src.backtesting.strategy_workflow import (
    run_regime_strategy_workflow
)

class TestStrategyWorkflow(unittest.TestCase):

    def make_comparison_result(self):
        return {
            "total_strategies": 2,
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
                ]
            }
        }

    def make_validation_result(self):
        return {
            "selected_strategy": {
                "strategy": "EMA 5/20"
            },
            "testing_report": {
                "total_trades": 12,
                "net_pnl": 250,
                "return_percent": 2.5,
                "max_drawdown_percent": 2.0
            }
        }

    def make_walk_forward_result(self):
        return {
            "fold_results": [
                {
                    "fold": 1,
                    "selected_strategy": "EMA 5/20",
                    "testing_report": {
                        "total_trades": 6,
                        "net_pnl": 100,
                        "max_drawdown_percent": 2.0
                    }
                },
                {
                    "fold": 2,
                    "selected_strategy": "EMA 5/20",
                    "testing_report": {
                        "total_trades": 6,
                        "net_pnl": 150,
                        "max_drawdown_percent": 3.0
                    }
                }
            ]
        }

    def setUp(self):
        self.df = pd.DataFrame({
            "timestamp": ["2026-01-01"],
            "symbol": ["TEST"]
        })

    @patch("src.backtesting.strategy_workflow.validate_strategy_evidence")
    @patch("src.backtesting.strategy_workflow.compare_strategies_by_market_regime")
    def test_selects_validated_strategy(
        self,
        mock_comparison,
        mock_validation
    ):
        mock_comparison.return_value = self.make_comparison_result()

        mock_validation.return_value = {
            "passed": True,
            "status": "PASSED",
            "reasons": []
        }

        result = run_regime_strategy_workflow(
            self.df,
            "TRENDING_UP",
            self.make_validation_result(),
            self.make_walk_forward_result()
        )

        self.assertEqual(result["status"], "SELECTED")
        self.assertEqual(
            result["selected_strategy"]["strategy"],
            "EMA 5/20"
        )
        self.assertEqual(result["total_candidates"], 2)
        self.assertEqual(result["validated_candidates"], 2)

    @patch("src.backtesting.strategy_workflow.validate_strategy_evidence")
    @patch("src.backtesting.strategy_workflow.compare_strategies_by_market_regime")
    def test_returns_no_trade_when_validation_fails(
        self,
        mock_comparison,
        mock_validation
    ):
        mock_comparison.return_value = self.make_comparison_result()

        mock_validation.return_value = {
            "passed": False,
            "status": "FAILED",
            "reasons": ["Insufficient validation evidence."]
        }

        result = run_regime_strategy_workflow(
            self.df,
            "TRENDING_UP",
            self.make_validation_result(),
            self.make_walk_forward_result()
        )

        self.assertEqual(result["status"], "NO_TRADE")
        self.assertIsNone(result["selected_strategy"])
        self.assertEqual(result["validated_candidates"], 0)

    @patch("src.backtesting.strategy_workflow.validate_strategy_evidence")
    @patch("src.backtesting.strategy_workflow.compare_strategies_by_market_regime")
    def test_only_current_regime_candidates_are_validated(
        self,
        mock_comparison,
        mock_validation
    ):
        mock_comparison.return_value = self.make_comparison_result()

        mock_validation.return_value = {
            "passed": True,
            "reasons": []
        }

        run_regime_strategy_workflow(
            self.df,
            "TRENDING_UP",
            self.make_validation_result(),
            self.make_walk_forward_result()
        )

        self.assertEqual(mock_validation.call_count, 2)

    @patch("src.backtesting.strategy_workflow.compare_strategies_by_market_regime")
    def test_unknown_regime_returns_no_trade(self, mock_comparison):
        mock_comparison.return_value = self.make_comparison_result()

        result = run_regime_strategy_workflow(
            self.df,
            "HIGH_VOLATILITY",
            self.make_validation_result(),
            self.make_walk_forward_result()
        )

        self.assertEqual(result["status"], "NO_TRADE")
        self.assertIsNone(result["selected_strategy"])
        self.assertEqual(result["total_candidates"], 0)

    @patch("src.backtesting.strategy_workflow.validate_strategy_evidence")
    @patch("src.backtesting.strategy_workflow.compare_strategies_by_market_regime")
    def test_validates_each_strategy_with_its_own_evidence(
        self,
        mock_comparison,
        mock_validation
    ):
        mock_comparison.return_value = self.make_comparison_result()

        mock_validation.side_effect = [
            {
                "passed": True,
                "status": "PASSED",
                "reasons": []
            },
            {
                "passed": False,
                "status": "FAILED",
                "reasons": ["Drawdown exceeded."]
            }
        ]

        evidence = {
            "EMA 5/20": {
                "out_of_sample_result": self.make_validation_result(),
                "walk_forward_result": self.make_walk_forward_result()
            },
            "EMA 9/21": {
                "out_of_sample_result": self.make_validation_result(),
                "walk_forward_result": self.make_walk_forward_result()
            }
        }

        result = run_regime_strategy_workflow(
            self.df,
            "TRENDING_UP",
            validation_data_by_strategy=evidence
        )

        self.assertEqual(mock_validation.call_count, 2)
        self.assertTrue(
            result["validation_results"]["EMA 5/20"]["passed"]
        )
        self.assertFalse(
            result["validation_results"]["EMA 9/21"]["passed"]
        )
        self.assertEqual(result["validated_candidates"], 1)

    @patch("src.backtesting.strategy_workflow.validate_strategy_evidence")
    @patch("src.backtesting.strategy_workflow.compare_strategies_by_market_regime")
    def test_missing_candidate_evidence_fails_safely(
        self,
        mock_comparison,
        mock_validation
    ):
        mock_comparison.return_value = self.make_comparison_result()

        mock_validation.return_value = {
            "passed": True,
            "status": "PASSED",
            "reasons": []
        }

        evidence = {
            "EMA 5/20": {
                "out_of_sample_result": self.make_validation_result(),
                "walk_forward_result": self.make_walk_forward_result()
            }
        }

        result = run_regime_strategy_workflow(
            self.df,
            "TRENDING_UP",
            validation_data_by_strategy=evidence
        )

        self.assertTrue(
            result["validation_results"]["EMA 5/20"]["passed"]
        )
        self.assertFalse(
            result["validation_results"]["EMA 9/21"]["passed"]
        )
        self.assertEqual(result["validated_candidates"], 1)

    @patch("src.backtesting.strategy_workflow.validate_strategy_evidence")
    @patch("src.backtesting.strategy_workflow.compare_strategies_by_market_regime")
    def test_rejected_validation_evidence_fails_safely(
        self,
        mock_comparison,
        mock_validation
    ):
        mock_comparison.return_value = self.make_comparison_result()

        mock_validation.side_effect = ValueError(
            "Invalid validation metrics."
        )

        evidence = {
            name: {
                "out_of_sample_result": self.make_validation_result(),
                "walk_forward_result": self.make_walk_forward_result()
            }
            for name in ["EMA 5/20", "EMA 9/21"]
        }

        result = run_regime_strategy_workflow(
            self.df,
            "TRENDING_UP",
            validation_data_by_strategy=evidence
        )

        self.assertEqual(result["validated_candidates"], 0)
        self.assertEqual(result["status"], "NO_TRADE")

    def test_rejects_invalid_independent_evidence_container(self):
        with self.assertRaises(ValueError):
            run_regime_strategy_workflow(
                self.df,
                "TRENDING_UP",
                validation_data_by_strategy="invalid"
            )

    def test_rejects_empty_market_data(self):
        with self.assertRaises(ValueError):
            run_regime_strategy_workflow(
                pd.DataFrame(),
                "TRENDING_UP",
                self.make_validation_result(),
                self.make_walk_forward_result()
            )

    def test_rejects_invalid_validation_settings(self):
        with self.assertRaises(ValueError):
            run_regime_strategy_workflow(
                self.df,
                "TRENDING_UP",
                self.make_validation_result(),
                self.make_walk_forward_result(),
                validation_kwargs="invalid"
            )

    def test_rejects_reserved_validation_parameters(self):
        with self.assertRaises(ValueError):
            run_regime_strategy_workflow(
                self.df,
                "TRENDING_UP",
                self.make_validation_result(),
                self.make_walk_forward_result(),
                validation_kwargs={
                    "strategy_name": "EMA 5/20"
                }
            )

    def test_rejects_invalid_drawdown_limit(self):
        with self.assertRaises(ValueError):
            run_regime_strategy_workflow(
                self.df,
                "TRENDING_UP",
                self.make_validation_result(),
                self.make_walk_forward_result(),
                max_drawdown_percent=-1
            )

    
    @patch("src.backtesting.strategy_workflow.validate_strategy_evidence")
    @patch("src.backtesting.strategy_workflow.run_walk_forward_validation")
    @patch("src.backtesting.strategy_workflow.run_out_of_sample_validation")
    @patch("src.backtesting.strategy_workflow.compare_strategies_by_market_regime")
    def test_automatically_generates_independent_evidence(
        self,
        mock_comparison,
        mock_oos,
        mock_walk_forward,
        mock_validation
    ):
        comparison = self.make_comparison_result()

        comparison["strategy_details"] = [
            {
                "strategy": "EMA 5/20",
                "fast_period": 5,
                "slow_period": 20
            },
            {
                "strategy": "EMA 9/21",
                "fast_period": 9,
                "slow_period": 21
            }
        ]

        mock_comparison.return_value = comparison

        mock_oos.side_effect = [
            self.make_validation_result(),
            self.make_validation_result()
        ]

        mock_walk_forward.side_effect = [
            self.make_walk_forward_result(),
            self.make_walk_forward_result()
        ]

        mock_validation.return_value = {
            "passed": True,
            "status": "PASSED",
            "reasons": []
        }

        result = run_regime_strategy_workflow(
            self.df,
            "TRENDING_UP"
        )

        self.assertEqual(result["validation_mode"], "automatic")
        self.assertEqual(mock_oos.call_count, 2)
        self.assertEqual(mock_walk_forward.call_count, 2)
        self.assertEqual(mock_validation.call_count, 2)

        first_config = mock_oos.call_args_list[0].kwargs[
            "strategy_configs"
        ][0]

        second_config = mock_oos.call_args_list[1].kwargs[
            "strategy_configs"
        ][0]

        self.assertEqual(first_config["name"], "EMA 5/20")
        self.assertEqual(second_config["name"], "EMA 9/21")

    @patch("src.backtesting.strategy_workflow.compare_strategies_by_market_regime")
    def test_automatic_validation_missing_strategy_details(
        self,
        mock_comparison
    ):
        mock_comparison.return_value = self.make_comparison_result()

        with self.assertRaises(ValueError):
            run_regime_strategy_workflow(
                self.df,
                "TRENDING_UP"
            )

    @patch("src.backtesting.strategy_workflow.validate_strategy_evidence")
    @patch("src.backtesting.strategy_workflow.run_walk_forward_validation")
    @patch("src.backtesting.strategy_workflow.run_out_of_sample_validation")
    @patch("src.backtesting.strategy_workflow.compare_strategies_by_market_regime")
    def test_automatic_validation_failure_returns_no_trade(
        self,
        mock_comparison,
        mock_oos,
        mock_walk_forward,
        mock_validation
    ):
        comparison = self.make_comparison_result()

        comparison["strategy_details"] = [
            {
                "strategy": "EMA 5/20",
                "fast_period": 5,
                "slow_period": 20
            },
            {
                "strategy": "EMA 9/21",
                "fast_period": 9,
                "slow_period": 21
            }
        ]

        mock_comparison.return_value = comparison

        mock_oos.return_value = self.make_validation_result()
        mock_walk_forward.return_value = self.make_walk_forward_result()

        mock_validation.side_effect = ValueError(
            "Insufficient validation evidence."
        )

        result = run_regime_strategy_workflow(
            self.df,
            "TRENDING_UP"
        )

        self.assertEqual(result["status"], "NO_TRADE")
        self.assertIsNone(result["selected_strategy"])
        self.assertEqual(result["validated_candidates"], 0)

    @patch("src.backtesting.strategy_workflow.run_out_of_sample_validation")
    @patch("src.backtesting.strategy_workflow.compare_strategies_by_market_regime")
    def test_automatic_validation_missing_candidate_configuration(
        self,
        mock_comparison,
        mock_oos
    ):
        comparison = self.make_comparison_result()

        comparison["strategy_details"] = [
            {
                "strategy": "EMA 5/20",
                "fast_period": 5,
                "slow_period": 20
            }
        ]

        mock_comparison.return_value = comparison

        result = run_regime_strategy_workflow(
            self.df,
            "TRENDING_UP"
        )

        self.assertFalse(
            result["validation_results"]["EMA 9/21"]["passed"]
        )

        self.assertEqual(mock_oos.call_count, 1)


if __name__ == "__main__":
    unittest.main()