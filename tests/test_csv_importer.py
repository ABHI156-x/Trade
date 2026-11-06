
import unittest
import pandas as pd
import tempfile

from pathlib import Path

from src.market_data.csv_importer import import_historical_csv


class TestCSVImporter(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.file_path = Path(self.temp_dir.name) / "history.csv"

        df = pd.DataFrame({
            "timestamp": [
                "2026-11-04 09:20:00",
                "2026-11-04 09:15:00"
            ],
            "open": [101, 100],
            "high": [103, 102],
            "low": [99, 98],
            "close": [102, 101],
            "volume": [1000, 1200]
        })

        df.to_csv(self.file_path, index=False)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_successful_import(self):

        result = import_historical_csv(
            self.file_path,
            "RELIANCE",
            "NSE"
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]["symbol"], "RELIANCE")
        self.assertEqual(result.iloc[0]["exchange"], "NSE")

    def test_timestamp_sorting(self):

        result = import_historical_csv(
            self.file_path,
            "RELIANCE"
        )

        self.assertTrue(
            result["timestamp"].is_monotonic_increasing
        )

    def test_invalid_exchange(self):

        with self.assertRaises(ValueError):

            import_historical_csv(
                self.file_path,
                "RELIANCE",
                "NYSE"
            )

    def test_missing_file(self):

        with self.assertRaises(FileNotFoundError):

            import_historical_csv(
                "missing.csv",
                "RELIANCE"
            )

    def test_invalid_ohlc(self):

        df = pd.read_csv(self.file_path)

        df.loc[0, "high"] = 90

        df.to_csv(self.file_path, index=False)

        with self.assertRaises(ValueError):

            import_historical_csv(
                self.file_path,
                "RELIANCE"
            )


if __name__ == "__main__":
    unittest.main()
