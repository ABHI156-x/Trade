
import unittest
import pandas as pd

from src.paper_trading.auto_trader import AutoPaperTrader


class TestAutoPaperTrader(unittest.TestCase):

    def make_data(self, symbols=("RELIANCE",)):

        rows = []

        candles = [
            {
                "time": "09:15",
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "ema9": 9,
                "ema21": 10
            },
            {
                "time": "09:20",
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "ema9": 11,
                "ema21": 10
            },
            {
                "time": "09:25",
                "open": 100,
                "high": 103,
                "low": 100,
                "close": 102.5,
                "ema9": 11,
                "ema21": 10
            }
        ]

        for symbol in symbols:

            for candle in candles:

                rows.append({
                    "timestamp": pd.Timestamp(
                        f"2026-11-04 {candle['time']}:00"
                    ),
                    "symbol": symbol,
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "EMA_9": candle["ema9"],
                    "EMA_21": candle["ema21"]
                })

        return pd.DataFrame(rows)

    def test_automatic_entry_and_target(self):

        trader = AutoPaperTrader(
            initial_capital=10000,
            risk_per_trade=100,
            brokerage_per_order=0,
            charges_rate=0,
            slippage_per_share=0
        )

        report = trader.run(self.make_data())

        self.assertEqual(report["total_trades"], 1)

        trade = report["trade_history"][0]

        self.assertEqual(trade["symbol"], "RELIANCE")
        self.assertEqual(trade["reason"], "TARGET")
        self.assertEqual(trade["quantity"], 100)
        self.assertAlmostEqual(trade["net_pnl"], 200)

        self.assertEqual(report["final_capital"], 10200)
        self.assertEqual(report["remaining_positions"], 0)

    def test_no_signal_means_no_trade(self):

        df = self.make_data()

        df["EMA_9"] = 8
        df["EMA_21"] = 10

        trader = AutoPaperTrader()

        report = trader.run(df)

        self.assertEqual(report["total_trades"], 0)
        self.assertEqual(report["final_capital"], 10000)

    def test_shared_capital(self):

        trader = AutoPaperTrader(
            initial_capital=10000,
            risk_per_trade=100,
            brokerage_per_order=0,
            charges_rate=0,
            slippage_per_share=0
        )

        report = trader.run(
            self.make_data(("AAA", "BBB"))
        )

        self.assertEqual(report["total_trades"], 1)
        self.assertEqual(
            report["trade_history"][0]["symbol"],
            "AAA"
        )
        self.assertEqual(report["blocked_entries"], 1)


if __name__ == "__main__":
    unittest.main()
