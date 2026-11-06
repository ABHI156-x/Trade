
import pandas as pd
from pathlib import Path


class TradeJournal:

    def __init__(self, file_path="data/trade_journal.csv"):

        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

    def save_trade(self, trade):

        df = pd.DataFrame([trade])

        df.to_csv(
            self.file_path,
            mode="a",
            header=not self.file_path.exists(),
            index=False
        )

        return True

    def save_trades(self, trades):

        if not trades:
            return 0

        df = pd.DataFrame(trades)

        df.to_csv(
            self.file_path,
            mode="a",
            header=not self.file_path.exists(),
            index=False
        )

        return len(df)

    def read_trades(self):

        if not self.file_path.exists():
            return pd.DataFrame()

        return pd.read_csv(self.file_path)
