
import unittest

from src.risk.trading_costs import (
    calculate_indian_equity_intraday_costs
)


class TestIndianTradingCosts(unittest.TestCase):

    def test_nse_intraday_cost_calculation(self):

        result = calculate_indian_equity_intraday_costs(
            entry_price=1000,
            exit_price=1020,
            quantity=10,
            exchange="NSE",
            slippage_per_share=0
        )

        self.assertEqual(result["buy_turnover"], 10000)
        self.assertEqual(result["sell_turnover"], 10200)

        self.assertEqual(result["brokerage_buy"], 10)
        self.assertEqual(result["brokerage_sell"], 10.2)

        self.assertEqual(result["stt"], 2.55)
        self.assertEqual(result["stamp_duty"], 0.30)

        self.assertGreater(result["total_cost"], 0)
        self.assertEqual(
            result["net_pnl"],
            round(result["gross_pnl"] - result["total_cost"], 2)
        )

    def test_bse_intraday_cost_calculation(self):

        result = calculate_indian_equity_intraday_costs(
            entry_price=1000,
            exit_price=1020,
            quantity=10,
            exchange="BSE",
            slippage_per_share=0
        )

        self.assertEqual(result["exchange"], "BSE")
        self.assertGreater(result["exchange_charges"], 0)
        self.assertEqual(result["ipft_charges"], 0)

    def test_slippage_is_included(self):

        without_slippage = calculate_indian_equity_intraday_costs(
            1000, 1020, 10, slippage_per_share=0
        )

        with_slippage = calculate_indian_equity_intraday_costs(
            1000, 1020, 10, slippage_per_share=0.50
        )

        self.assertEqual(
            round(
                with_slippage["total_cost"]
                - without_slippage["total_cost"],
                2
            ),
            10
        )

    def test_invalid_exchange(self):

        with self.assertRaises(ValueError):
            calculate_indian_equity_intraday_costs(
                1000, 1020, 10, exchange="INVALID"
            )

    def test_negative_slippage(self):

        with self.assertRaises(ValueError):
            calculate_indian_equity_intraday_costs(
                1000, 1020, 10, slippage_per_share=-1
            )

    def test_zero_quantity(self):

        with self.assertRaises(ValueError):
            calculate_indian_equity_intraday_costs(
                1000, 1020, 0
            )

    def test_fractional_quantity(self):

        with self.assertRaises(ValueError):
            calculate_indian_equity_intraday_costs(
                1000, 1020, 1.5
            )


if __name__ == "__main__":
    unittest.main()
