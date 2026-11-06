
import unittest
import tempfile
from pathlib import Path
import pandas as pd

from src.paper_trading.replay_runner import PaperReplayRunner
from src.utils.trade_logger import close_trade_logger


class TestPaperReplayRunner(unittest.TestCase):

    def make_data(self):
        return pd.DataFrame([
            {
                "timestamp": pd.Timestamp("2026-11-04 09:15"),
                "symbol": "RELIANCE",
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "EMA_9": 9,
                "EMA_21": 10
            },
            {
                "timestamp": pd.Timestamp("2026-11-04 09:20"),
                "symbol": "RELIANCE",
                "open": 100,
                "high": 100.5,
                "low": 99.5,
                "close": 100,
                "EMA_9": 11,
                "EMA_21": 10
            },
            {
                "timestamp": pd.Timestamp("2026-11-04 09:25"),
                "symbol": "RELIANCE",
                "open": 100,
                "high": 103,
                "low": 100,
                "close": 102.5,
                "EMA_9": 11,
                "EMA_21": 10
            }
        ])

    def test_replay_and_journal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                runner = PaperReplayRunner(
                    initial_capital=10000,
                    risk_per_trade=100,
                    journal_path=str(Path(temp_dir) / "trades.csv"),
                    log_path=str(Path(temp_dir) / "trading.log")
                )

                report = runner.run(self.make_data())

                self.assertEqual(report["total_trades"], 1)
                self.assertEqual(
                    report["trade_history"][0]["reason"],
                    "TARGET"
                )

                saved_trades = runner.journal.read_trades()

                self.assertEqual(len(saved_trades), 1)
                self.assertEqual(
                    saved_trades.iloc[0]["symbol"],
                    "RELIANCE"
                )

            finally:
                close_trade_logger()


if __name__ == "__main__":
    unittest.main()
