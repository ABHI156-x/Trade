
import unittest
import tempfile
from pathlib import Path

from src.paper_trading.trade_journal import TradeJournal


class TestTradeJournal(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = Path(self.temp_dir.name) / "trades.csv"
        self.journal = TradeJournal(self.file_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_single_trade(self):

        trade = {
            "symbol": "RELIANCE",
            "entry": 100,
            "exit": 102,
            "quantity": 10,
            "net_pnl": 20
        }

        self.assertTrue(self.journal.save_trade(trade))

        result = self.journal.read_trades()

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["symbol"], "RELIANCE")

    def test_save_multiple_trades(self):

        trades = [
            {"symbol": "TCS", "net_pnl": 50},
            {"symbol": "INFY", "net_pnl": -20}
        ]

        saved = self.journal.save_trades(trades)

        self.assertEqual(saved, 2)
        self.assertEqual(len(self.journal.read_trades()), 2)

    def test_empty_journal(self):

        result = self.journal.read_trades()

        self.assertTrue(result.empty)

    def test_append_trades(self):

        self.journal.save_trade({"symbol": "TCS", "net_pnl": 50})
        self.journal.save_trade({"symbol": "INFY", "net_pnl": 20})

        result = self.journal.read_trades()

        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
