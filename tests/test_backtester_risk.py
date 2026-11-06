
import unittest
import pandas as pd

from src.backtesting.backtester import run_backtest


class TestBacktesterRisk(unittest.TestCase):

    def test_gap_stop_is_recorded(self):

        df = pd.DataFrame([
            {
                "timestamp": "2026-11-04 09:15",
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "EMA_9": 9,
                "EMA_21": 10
            },
            {
                "timestamp": "2026-11-04 09:20",
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 100,
                "EMA_9": 11,
                "EMA_21": 10
            },
            {
                "timestamp": "2026-11-04 09:25",
                "open": 98,
                "high": 99,
                "low": 97,
                "close": 98,
                "EMA_9": 10,
                "EMA_21": 10
            }
        ])

        report = run_backtest(
            df,
            initial_capital=10000,
            risk_per_trade=10,
            brokerage_per_order=0,
            charges_rate=0,
            slippage_per_share=0
        )

        self.assertEqual(report["total_trades"], 1)

        trade = report["trade_history"][0]

        self.assertEqual(trade["reason"], "STOP_LOSS_GAP")
        self.assertEqual(trade["exit"], 98)

        self.assertEqual(
            report["daily_risk_report"]["trades_taken"],
            1
        )


if __name__ == "__main__":
    unittest.main()
