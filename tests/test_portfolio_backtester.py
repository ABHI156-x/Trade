
import unittest
import pandas as pd
import json

from src.backtesting.portfolio_backtester import (
    run_portfolio_backtest
)


class TestPortfolioBacktester(unittest.TestCase):

    def load_cost_settings(self):

        with open("config/settings.json", "r") as file:
            settings = json.load(file)

        return settings["costs"]

    def make_single_stock_data(self, exchange="NSE"):

        return pd.DataFrame([
            {
                "timestamp": "2026-11-04 09:15:00",
                "symbol": "TEST",
                "exchange": exchange,
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "EMA_9": 9,
                "EMA_21": 10
            },
            {
                "timestamp": "2026-11-04 09:20:00",
                "symbol": "TEST",
                "exchange": exchange,
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "EMA_9": 11,
                "EMA_21": 10
            },
            {
                "timestamp": "2026-11-04 09:25:00",
                "symbol": "TEST",
                "exchange": exchange,
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "EMA_9": 11,
                "EMA_21": 10
            }
        ])

    def test_multiple_stocks_share_capital(self):

        df = pd.DataFrame([

            # First candle: no entry signal
            {
                "timestamp": "2026-11-04 09:15:00",
                "symbol": "AAA",
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "EMA_9": 9,
                "EMA_21": 10
            },
            {
                "timestamp": "2026-11-04 09:15:00",
                "symbol": "BBB",
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "EMA_9": 9,
                "EMA_21": 10
            },

            # Second candle: both stocks generate bullish crossovers
            {
                "timestamp": "2026-11-04 09:20:00",
                "symbol": "AAA",
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "EMA_9": 11,
                "EMA_21": 10
            },
            {
                "timestamp": "2026-11-04 09:20:00",
                "symbol": "BBB",
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "EMA_9": 11,
                "EMA_21": 10
            },

            # Third candle: positions remain open
            {
                "timestamp": "2026-11-04 09:25:00",
                "symbol": "AAA",
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "EMA_9": 11,
                "EMA_21": 10
            },
            {
                "timestamp": "2026-11-04 09:25:00",
                "symbol": "BBB",
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "EMA_9": 11,
                "EMA_21": 10
            }

        ])

        report = run_portfolio_backtest(
            df,
            initial_capital=1500,
            risk_per_trade=10,
            brokerage_per_order=0,
            charges_rate=0,
            slippage_per_share=0,
            max_daily_loss=500,
            max_trades_per_day=3
        )

        self.assertEqual(report["total_trades"], 2)

        quantities = {
            trade["symbol"]: trade["quantity"]
            for trade in report["trade_history"]
        }

        self.assertEqual(quantities["AAA"], 10)
        self.assertEqual(quantities["BBB"], 5)

        total_investment = sum(
            trade["entry"] * trade["quantity"]
            for trade in report["trade_history"]
        )

        self.assertLessEqual(total_investment, 1500)

        self.assertEqual(report["remaining_positions"], 0)

        self.assertAlmostEqual(report["final_capital"], 1500)

    def test_indian_transaction_costs_are_applied(self):

        df = self.make_single_stock_data("NSE")
        cost_settings = self.load_cost_settings()

        report = run_portfolio_backtest(
            df,
            initial_capital=10000,
            risk_per_trade=100,
            max_daily_loss=500,
            max_trades_per_day=3,
            cost_settings=cost_settings
        )

        self.assertEqual(report["total_trades"], 1)

        trade = report["trade_history"][0]

        self.assertEqual(trade["exchange"], "NSE")

        self.assertGreater(trade["total_cost"], 0)

        self.assertGreater(trade["brokerage"], 0)

        self.assertGreater(trade["stt"], 0)

        self.assertGreater(trade["stamp_duty"], 0)

        self.assertGreater(trade["gst"], 0)

        self.assertAlmostEqual(
            report["final_capital"],
            report["initial_capital"] + report["net_pnl"],
            places=2
        )

        self.assertAlmostEqual(
            report["total_costs"],
            trade["total_cost"],
            places=2
        )

    def test_nse_and_bse_exchange_charges(self):

        cost_settings = self.load_cost_settings()

        nse_report = run_portfolio_backtest(
            self.make_single_stock_data("NSE"),
            initial_capital=10000,
            risk_per_trade=100,
            cost_settings=cost_settings
        )

        bse_report = run_portfolio_backtest(
            self.make_single_stock_data("BSE"),
            initial_capital=10000,
            risk_per_trade=100,
            cost_settings=cost_settings
        )

        nse_trade = nse_report["trade_history"][0]
        bse_trade = bse_report["trade_history"][0]

        self.assertEqual(nse_trade["exchange"], "NSE")
        self.assertEqual(bse_trade["exchange"], "BSE")

        self.assertGreater(
            bse_trade["exchange_charges"],
            nse_trade["exchange_charges"]
        )

        expected_nse_charges = round(
            (
                nse_trade["buy_turnover"]
                + nse_trade["sell_turnover"]
            )
            * cost_settings["exchange_transaction_rate"]["NSE"],
            2
        )

        expected_bse_charges = round(
            (
                bse_trade["buy_turnover"]
                + bse_trade["sell_turnover"]
            )
            * cost_settings["exchange_transaction_rate"]["BSE"],
            2
        )

        self.assertAlmostEqual(
            nse_trade["exchange_charges"],
            expected_nse_charges,
            places=2
        )

        self.assertAlmostEqual(
            bse_trade["exchange_charges"],
            expected_bse_charges,
            places=2
        )


if __name__ == "__main__":
    unittest.main()
