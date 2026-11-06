
import unittest
import pandas as pd

from src.analysis.market_regime import (
    classify_market_regime,
    classify_regimes_by_symbol
)


class TestMarketRegime(unittest.TestCase):

    def make_data(self, prices=None):
        if prices is None:
            prices = [100 + i for i in range(40)]

        return pd.DataFrame({
            "timestamp": pd.date_range(
                "2026-01-01",
                periods=len(prices),
                freq="D"
            ),
            "symbol": "TEST",
            "high": [p + 0.2 for p in prices],
            "low": [p - 0.2 for p in prices],
            "close": prices
        })

    def test_calculates_regime_columns(self):
        df = self.make_data()

        result = classify_market_regime(df)

        self.assertIn("ATR", result.columns)
        self.assertIn("ATR_PERCENT", result.columns)
        self.assertIn("TREND_STRENGTH", result.columns)
        self.assertIn("MARKET_REGIME", result.columns)

    def test_detects_uptrend(self):
        prices = [100 + i for i in range(40)]
        df = self.make_data(prices)

        result = classify_market_regime(
            df,
            volatility_threshold=10
        )

        self.assertEqual(
            result.iloc[-1]["MARKET_REGIME"],
            "TRENDING_UP"
        )

    def test_detects_downtrend(self):
        prices = [150 - i for i in range(40)]
        df = self.make_data(prices)

        result = classify_market_regime(
            df,
            volatility_threshold=10
        )

        self.assertEqual(
            result.iloc[-1]["MARKET_REGIME"],
            "TRENDING_DOWN"
        )

    def test_detects_high_volatility(self):
        prices = [100] * 20

        df = self.make_data(prices)
        df["high"] = 105
        df["low"] = 95

        result = classify_market_regime(
            df,
            volatility_threshold=1
        )

        self.assertEqual(
            result.iloc[-1]["MARKET_REGIME"],
            "HIGH_VOLATILITY"
        )

    def test_detects_sideways_market(self):
        prices = [100 + (0.01 if i % 2 else 0) for i in range(40)]

        df = self.make_data(prices)

        result = classify_market_regime(
            df,
            trend_threshold=1,
            volatility_threshold=10
        )

        self.assertEqual(
            result.iloc[-1]["MARKET_REGIME"],
            "SIDEWAYS"
        )

    def test_initial_rows_are_unknown(self):
        df = self.make_data()

        result = classify_market_regime(
            df,
            atr_period=14
        )

        self.assertEqual(
            result.iloc[0]["MARKET_REGIME"],
            "UNKNOWN"
        )

    def test_rejects_invalid_periods(self):
        df = self.make_data()

        with self.assertRaises(ValueError):
            classify_market_regime(df, fast_period=0)

        with self.assertRaises(ValueError):
            classify_market_regime(
                df,
                fast_period=21,
                slow_period=9
            )

    def test_processes_symbols_independently(self):
        df1 = self.make_data()
        df1["symbol"] = "AAA"

        df2 = self.make_data(
            [200 + i for i in range(40)]
        )
        df2["symbol"] = "BBB"

        df = pd.concat([df1, df2], ignore_index=True)

        result = classify_regimes_by_symbol(df)

        self.assertEqual(
            result["symbol"].nunique(),
            2
        )

        self.assertEqual(len(result), 80)


if __name__ == "__main__":
    unittest.main()
