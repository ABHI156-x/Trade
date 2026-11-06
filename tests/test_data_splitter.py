
import unittest
import pandas as pd

from src.backtesting.data_splitter import split_market_data


class TestDataSplitter(unittest.TestCase):

    def setUp(self):

        rows = []

        for timestamp in pd.date_range(
            "2026-11-04 09:15",
            periods=10,
            freq="5min"
        ):

            for symbol in ["RELIANCE", "TCS"]:

                rows.append({
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "close": 100
                })

        self.df = pd.DataFrame(rows)

    def test_split_row_counts(self):

        train, test = split_market_data(
            self.df,
            0.70
        )

        self.assertEqual(len(train), 14)
        self.assertEqual(len(test), 6)

    def test_no_timestamp_overlap(self):

        train, test = split_market_data(self.df)

        train_times = set(train["timestamp"])
        test_times = set(test["timestamp"])

        self.assertTrue(train_times.isdisjoint(test_times))

    def test_chronological_split(self):

        train, test = split_market_data(self.df)

        self.assertLess(
            train["timestamp"].max(),
            test["timestamp"].min()
        )

    def test_invalid_ratio(self):

        with self.assertRaises(ValueError):
            split_market_data(self.df, 1.5)

    def test_empty_data(self):

        with self.assertRaises(ValueError):
            split_market_data(pd.DataFrame())

    def test_one_timestamp(self):

        df = self.df[
            self.df["timestamp"] == self.df["timestamp"].min()
        ]

        with self.assertRaises(ValueError):
            split_market_data(df)


if __name__ == "__main__":
    unittest.main()
