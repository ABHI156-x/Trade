
import json
from pathlib import Path

from src.paper_trading.auto_trader import AutoPaperTrader
from src.paper_trading.trade_journal import TradeJournal
from src.utils.trade_logger import get_trade_logger


class PaperReplayRunner:

    def __init__(
        self,
        initial_capital=10000,
        risk_per_trade=100,
        max_daily_loss=500,
        max_trades_per_day=3,
        journal_path="data/trade_journal.csv",
        log_path="logs/trading.log",
        settings_path="config/settings.json",
        cost_settings=None
    ):

        if cost_settings is None:
            settings_file = Path(settings_path)

            with settings_file.open("r", encoding="utf-8") as file:
                project_settings = json.load(file)

            cost_settings = project_settings.get("costs")

        self.trader = AutoPaperTrader(
            initial_capital=initial_capital,
            risk_per_trade=risk_per_trade,
            max_daily_loss=max_daily_loss,
            max_trades_per_day=max_trades_per_day,
            cost_settings=cost_settings
        )

        self.journal = TradeJournal(journal_path)
        self.logger = get_trade_logger(log_path)

    def run(self, market_data):

        self.logger.info("Starting paper replay")

        report = self.trader.run(market_data)

        saved_count = self.journal.save_trades(
            report["trade_history"]
        )

        self.logger.info(
            "Replay completed | Trades: %s | Saved: %s | Net P&L: %.2f",
            report["total_trades"],
            saved_count,
            report["net_pnl"]
        )

        return report
