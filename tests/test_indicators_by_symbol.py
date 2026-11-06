
import unittest
import pandas as pd

from src.analysis.indicators import calculate_indicators_by_symbol


class TestIndicatorsBySymbol(unittest.TestCase):

    def test_indicators_are_calculated_independently(self):

        df = pd.DataFrame([
            {
                "timestamp": "2026-11-04 09:15",
                "symbol": "RELIANCE",
                "close": 100,
                "volume": 1000
            },
            {
                "timestamp": "2026-11-04 09:15",
                "symbol": "TCS",
                "close": 500,
                "volume": 2000
            },
            {
                "timestamp": "2026-11-04 09:20",
                "symbol": "RELIANCE",
                "close": 110,
                "volume": 1200
            },
            {
                "timestamp": "2026-11-04 09:20",
                "symbol": "TCS",
                "close": 510,
                "volume": 2200
            }
        ])

        df["timestamp"] = pd.to_datetime(df["timestamp"])

        result = calculate_indicators_by_symbol(df)

        reliance = result[result["symbol"] == "RELIANCE"]
        tcs = result[result["symbol"] == "TCS"]

        self.assertEqual(len(reliance), 2)
        self.assertEqual(len(tcs), 2)

        self.assertEqual(
            reliance.iloc[0]["EMA_9"],
            100
        )

        self.assertEqual(
            tcs.iloc[0]["EMA_9"],
            500
        )

        self.assertEqual(
            reliance.iloc[1]["EMA_9"],
            102
        )

        self.assertEqual(
            tcs.iloc[1]["EMA_9"],
            502
        )


if __name__ == "__main__":
    unittest.main()
