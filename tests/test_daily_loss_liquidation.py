
import unittest
import pandas as pd

from src.backtesting.backtester import run_backtest


class TestDailyLossLiquidation(unittest.TestCase):

    def test_open_position_closed_at_daily_loss_limit(self):

        df = pd.DataFrame([
            {
                "timestamp": pd.Timestamp("2026-11-04 09:15:00"),
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "EMA_9": 9,
                "EMA_21": 10
            },
            {
                "timestamp": pd.Timestamp("2026-11-04 09:20:00"),
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "EMA_9": 11,
                "EMA_21": 10
            },
            {
                "timestamp": pd.Timestamp("2026-11-04 09:25:00"),
                "open": 100,
                "high": 100.5,
                "low": 99.1,
                "close": 99.2,
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
            slippage_per_share=0,
            max_daily_loss=5,
            max_trades_per_day=3
        )

        self.assertEqual(report["total_trades"], 1)

        trade = report["trade_history"][0]

        self.assertEqual(
            trade["reason"],
            "DAILY_LOSS_SQUARE_OFF"
        )

        self.assertAlmostEqual(trade["exit"], 99.2)
        self.assertAlmostEqual(trade["net_pnl"], -8.0)

        self.assertAlmostEqual(
            report["daily_risk_report"]["daily_loss"],
            8.0
        )


if __name__ == "__main__":
    unittest.main()
