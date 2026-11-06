import pandas as pd

from src.paper_trading.portfolio_paper_broker import PortfolioPaperBroker
from src.backtesting.execution import check_exit_conditions
from src.utils.market_session import (
    is_market_session,
    is_entry_allowed,
    is_square_off_time
)


class AutoPaperTrader:

    def __init__(
        self,
        initial_capital=10000,
        risk_per_trade=100,
        max_daily_loss=500,
        max_trades_per_day=3,
        stop_loss_percent=0.01,
        target_percent=0.02,
        brokerage_per_order=0,
        charges_rate=0,
        slippage_per_share=0,
        cost_settings=None
    ):
        self.broker = PortfolioPaperBroker(
            initial_capital=initial_capital,
            risk_per_trade=risk_per_trade,
            max_daily_loss=max_daily_loss,
            max_trades_per_day=max_trades_per_day,
            brokerage_per_order=brokerage_per_order,
            charges_rate=charges_rate,
            slippage_per_share=slippage_per_share,
            cost_settings=cost_settings
        )

        if not 0 < stop_loss_percent < 1:
            raise ValueError("Invalid stop-loss percentage")

        if target_percent <= 0:
            raise ValueError("Target percentage must be positive")

        self.stop_loss_percent = stop_loss_percent
        self.target_percent = target_percent

        self.previous_candles = {}
        self.last_prices = {}
        self.previous_timestamp = None
        self.daily_reports = []

    def process_snapshot(self, snapshot):
        snapshot = snapshot.sort_values("symbol")
        timestamp = snapshot["timestamp"].iloc[0]

        if not is_market_session(timestamp):
            return

        current_day = timestamp.date()

        # Close positions from the previous trading day.
        if (
            self.previous_timestamp is not None
            and self.previous_timestamp.date() != current_day
        ):
            self.broker.close_all_positions(
                self.last_prices,
                self.previous_timestamp,
                "END_OF_DAY"
            )

            self.daily_reports.append(
                self.broker.risk_guard.get_report()
            )

            self.broker.risk_guard.reset()
            self.previous_candles.clear()

        candles = {}

        for _, row in snapshot.iterrows():
            symbol = row["symbol"]
            candle = row.to_dict()

            candles[symbol] = candle
            self.last_prices[symbol] = candle["close"]

        closed_symbols = set()

        # Monitor existing positions.
        for symbol in list(self.broker.positions.keys()):
            if symbol not in candles:
                continue

            candle = candles[symbol]

            if is_square_off_time(timestamp):
                self.broker.close_position(
                    symbol,
                    candle["close"],
                    timestamp,
                    "TIME_SQUARE_OFF"
                )
                closed_symbols.add(symbol)
                continue

            result = check_exit_conditions(
                candle,
                self.broker.positions[symbol]
            )

            if result is not None:
                exit_price, reason = result

                self.broker.close_position(
                    symbol,
                    exit_price,
                    timestamp,
                    reason
                )

                closed_symbols.add(symbol)

        # Check total portfolio daily loss.
        unrealized = self.broker.calculate_unrealized_pnl(
            self.last_prices
        )

        if (
            self.broker.risk_guard.daily_loss(unrealized)
            >= self.broker.risk_guard.max_daily_loss
        ):
            self.broker.close_all_positions(
                self.last_prices,
                timestamp,
                "DAILY_LOSS_SQUARE_OFF"
            )

            closed_symbols.update(candles.keys())

        # Detect new bullish EMA crossovers.
        if is_entry_allowed(timestamp):
            for symbol, candle in candles.items():
                if symbol in closed_symbols:
                    continue

                if symbol in self.broker.positions:
                    continue

                previous = self.previous_candles.get(symbol)

                if previous is None:
                    continue

                values = [
                    previous["EMA_9"],
                    previous["EMA_21"],
                    candle["EMA_9"],
                    candle["EMA_21"]
                ]

                if pd.isna(values).any():
                    continue

                bullish_crossover = (
                    previous["EMA_9"] <= previous["EMA_21"]
                    and candle["EMA_9"] > candle["EMA_21"]
                )

                if not bullish_crossover:
                    continue

                entry = float(candle["close"])

                stop_loss = entry * (
                    1 - self.stop_loss_percent
                )

                target = entry * (
                    1 + self.target_percent
                )

                self.broker.open_position(
                    symbol=symbol,
                    entry_price=entry,
                    stop_loss=stop_loss,
                    target=target,
                    timestamp=timestamp,
                    current_prices=self.last_prices
                )

        self.previous_candles.update(candles)
        self.previous_timestamp = timestamp

    def run(self, df):
        required_columns = [
            "timestamp", "symbol",
            "open", "high", "low", "close",
            "EMA_9", "EMA_21"
        ]

        if df.empty:
            raise ValueError("Market data is empty")

        df = df.copy()

        for column in required_columns:
            if column not in df.columns:
                raise ValueError(f"Missing column: {column}")

        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            errors="coerce"
        )

        if df["timestamp"].isna().any():
            raise ValueError("Invalid timestamps")

        df["symbol"] = df["symbol"].astype(str).str.upper()

        for column in [
            "open", "high", "low", "close",
            "EMA_9", "EMA_21"
        ]:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        price_columns = ["open", "high", "low", "close"]

        if df[price_columns].isna().any().any():
            raise ValueError("Invalid OHLC values")

        if (df[price_columns] <= 0).any().any():
            raise ValueError("Prices must be positive")

        invalid_ohlc = (
            (df["high"] < df[["open", "close", "low"]].max(axis=1))
            | (df["low"] > df[["open", "close", "high"]].min(axis=1))
        )

        if invalid_ohlc.any():
            raise ValueError("Invalid OHLC candle")

        if df.duplicated(["symbol", "timestamp"]).any():
            raise ValueError("Duplicate symbol/timestamp rows")

        df = df.sort_values(
            ["timestamp", "symbol"]
        ).reset_index(drop=True)

        for timestamp, snapshot in df.groupby("timestamp"):
            self.process_snapshot(snapshot)

        # Close all remaining positions after data ends.
        if self.previous_timestamp is not None:
            self.broker.close_all_positions(
                self.last_prices,
                self.previous_timestamp,
                "END_OF_DATA"
            )

            self.daily_reports.append(
                self.broker.risk_guard.get_report()
            )

        return {
            "initial_capital": self.broker.initial_capital,
            "final_capital": self.broker.balance,
            "net_pnl": (
                self.broker.balance
                - self.broker.initial_capital
            ),
            "total_trades": len(self.broker.trade_history),
            "trade_history": self.broker.trade_history,
            "daily_reports": self.daily_reports,
            "blocked_entries": self.broker.blocked_entries,
            "remaining_positions": len(self.broker.positions)
        }