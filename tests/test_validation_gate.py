
import unittest

from src.backtesting.validation_gate import (
    validate_strategy_evidence
)


class TestValidationGate(unittest.TestCase):

    def make_oos(self):
        return {
            "selected_strategy": {
                "strategy": "EMA 5/20"
            },
            "testing_report": {
                "total_trades": 12,
                "net_pnl": 500,
                "return_percent": 5.0,
                "max_drawdown_percent": 2.0
            }
        }

    def make_walk_forward(self):
        return {
            "total_folds": 4,
            "fold_results": [
                {
                    "fold": 1,
                    "selected_strategy": "EMA 5/20",
                    "testing_report": {
                        "total_trades": 5,
                        "net_pnl": 200,
                        "max_drawdown_percent": 1.0
                    }
                },
                {
                    "fold": 2,
                    "selected_strategy": "EMA 5/20",
                    "testing_report": {
                        "total_trades": 5,
                        "net_pnl": 100,
                        "max_drawdown_percent": 2.0
                    }
                },
                {
                    "fold": 3,
                    "selected_strategy": "EMA 9/21",
                    "testing_report": {
                        "total_trades": 4,
                        "net_pnl": -50,
                        "max_drawdown_percent": 3.0
                    }
                },
                {
                    "fold": 4,
                    "selected_strategy": "EMA 5/20",
                    "testing_report": {
                        "total_trades": 5,
                        "net_pnl": 150,
                        "max_drawdown_percent": 1.5
                    }
                }
            ]
        }

    def validate(self, oos=None, wf=None, **kwargs):
        return validate_strategy_evidence(
            strategy_name="EMA 5/20",
            out_of_sample_result=oos or self.make_oos(),
            walk_forward_result=wf or self.make_walk_forward(),
            **kwargs
        )

    def test_passes_valid_evidence(self):
        result = self.validate()

        self.assertTrue(result["passed"])
        self.assertEqual(result["status"], "PASSED")

    def test_rejects_strategy_mismatch(self):
        oos = self.make_oos()
        oos["selected_strategy"]["strategy"] = "EMA 9/21"

        result = self.validate(oos=oos)

        self.assertFalse(result["passed"])

    def test_rejects_insufficient_oos_trades(self):
        oos = self.make_oos()
        oos["testing_report"]["total_trades"] = 5

        result = self.validate(oos=oos)

        self.assertFalse(result["passed"])

    def test_rejects_negative_oos_pnl(self):
        oos = self.make_oos()
        oos["testing_report"]["net_pnl"] = -100

        result = self.validate(oos=oos)

        self.assertFalse(result["passed"])

    def test_rejects_excessive_oos_drawdown(self):
        oos = self.make_oos()
        oos["testing_report"]["max_drawdown_percent"] = 8

        result = self.validate(oos=oos)

        self.assertFalse(result["passed"])

    def test_uses_only_matching_walk_forward_folds(self):
        result = self.validate()

        self.assertEqual(
            result["walk_forward"]["selected_folds"],
            3
        )

        self.assertEqual(
            result["walk_forward"]["total_trades"],
            15
        )

        self.assertEqual(
            result["walk_forward"]["net_pnl"],
            450
        )

    def test_rejects_too_few_matching_folds(self):
        wf = self.make_walk_forward()

        wf["fold_results"] = wf["fold_results"][:1]

        result = self.validate(wf=wf)

        self.assertFalse(result["passed"])

    def test_rejects_negative_walk_forward_pnl(self):
        wf = self.make_walk_forward()

        for fold in wf["fold_results"]:
            if fold["selected_strategy"] == "EMA 5/20":
                fold["testing_report"]["net_pnl"] = -100

        result = self.validate(wf=wf)

        self.assertFalse(result["passed"])

    def test_rejects_too_few_profitable_folds(self):
        wf = self.make_walk_forward()

        wf["fold_results"][1]["testing_report"]["net_pnl"] = -100
        wf["fold_results"][3]["testing_report"]["net_pnl"] = -100

        result = self.validate(wf=wf)

        self.assertFalse(result["passed"])

    def test_rejects_invalid_oos_metrics(self):
        oos = self.make_oos()
        oos["testing_report"]["net_pnl"] = float("nan")

        with self.assertRaises(ValueError):
            self.validate(oos=oos)

    def test_rejects_invalid_walk_forward_metrics(self):
        wf = self.make_walk_forward()
        wf["fold_results"][0]["testing_report"][
            "max_drawdown_percent"
        ] = float("nan")

        with self.assertRaises(ValueError):
            self.validate(wf=wf)

    def test_rejects_invalid_strategy_name(self):
        with self.assertRaises(ValueError):
            validate_strategy_evidence(
                "",
                self.make_oos(),
                self.make_walk_forward()
            )


if __name__ == "__main__":
    unittest.main()
