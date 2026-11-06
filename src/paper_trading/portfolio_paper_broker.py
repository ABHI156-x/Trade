
from src.risk.portfolio_risk_guard import PortfolioRiskGuard

from src.risk.trading_costs import (
    calculate_trading_costs,
    calculate_indian_equity_intraday_costs
)


class PortfolioPaperBroker:

    def __init__(
        self,
        initial_capital=10000,
        risk_per_trade=100,
        max_daily_loss=500,
        max_trades_per_day=3,
        brokerage_per_order=0,
        charges_rate=0,
        slippage_per_share=0,
        cost_settings=None
    ):

        if initial_capital <= 0 or risk_per_trade <= 0:
            raise ValueError("Capital and risk must be positive")

        self.initial_capital = initial_capital
        self.balance = initial_capital
        self.risk_per_trade = risk_per_trade

        self.brokerage_per_order = brokerage_per_order
        self.charges_rate = charges_rate
        self.slippage_per_share = slippage_per_share

        self.cost_settings = cost_settings

        self.risk_guard = PortfolioRiskGuard(
            max_daily_loss=max_daily_loss,
            max_trades=max_trades_per_day
        )

        self.positions = {}
        self.trade_history = []
        self.blocked_entries = 0

    @property
    def committed_capital(self):

        return sum(
            position["entry"] * position["quantity"]
            for position in self.positions.values()
        )

    def _calculate_position_costs(
        self,
        entry_price,
        exit_price,
        quantity,
        exchange="NSE"
    ):

        if self.cost_settings is None:

            return calculate_trading_costs(
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=quantity,
                brokerage_per_order=self.brokerage_per_order,
                charges_rate=self.charges_rate,
                slippage_per_share=self.slippage_per_share
            )

        settings = self.cost_settings
        brokerage = settings["brokerage"]

        return calculate_indian_equity_intraday_costs(
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            exchange=exchange,
            slippage_per_share=settings["slippage_per_share"],
            brokerage_rate=brokerage["rate"],
            brokerage_cap=brokerage["maximum_per_order"],
            brokerage_minimum=brokerage["minimum_per_order"],
            brokerage_minimum_rate=brokerage["minimum_rate"],
            stt_sell_rate=settings["stt_sell_rate"],
            stamp_duty_buy_rate=settings["stamp_duty_buy_rate"],
            exchange_transaction_rate=settings[
                "exchange_transaction_rate"
            ],
            sebi_turnover_rate=settings["sebi_turnover_rate"],
            ipft_rate=settings["ipft_rate"],
            gst_rate=settings["gst_rate"]
        )

    def calculate_unrealized_pnl(self, prices):

        total_pnl = 0

        for symbol, position in self.positions.items():

            if symbol not in prices:
                continue

            result = self._calculate_position_costs(
                entry_price=position["entry"],
                exit_price=prices[symbol],
                quantity=position["quantity"],
                exchange=position.get("exchange", "NSE")
            )

            total_pnl += result["net_pnl"]

        return total_pnl

    def open_position(
        self,
        symbol,
        entry_price,
        stop_loss,
        target,
        timestamp,
        current_prices=None,
        exchange="NSE"
    ):

        symbol = symbol.upper()
        exchange = exchange.upper()

        if symbol in self.positions:
            return {
                "status": "BLOCKED",
                "reason": "Position already open"
            }

        if min(entry_price, stop_loss, target) <= 0:
            raise ValueError("Prices must be positive")

        if not stop_loss < entry_price < target:
            raise ValueError("Invalid long position prices")

        if exchange not in ("NSE", "BSE"):
            raise ValueError("Exchange must be NSE or BSE")

        unrealized = self.calculate_unrealized_pnl(
            current_prices or {}
        )

        allowed, message = self.risk_guard.can_take_trade(unrealized)

        if not allowed:
            self.blocked_entries += 1
            return {
                "status": "BLOCKED",
                "reason": message
            }

        available_capital = (
            self.balance - self.committed_capital
        )

        risk_per_share = entry_price - stop_loss

        risk_quantity = int(
            self.risk_per_trade // risk_per_share
        )

        capital_quantity = int(
            available_capital // entry_price
        )

        quantity = min(risk_quantity, capital_quantity)

        if quantity <= 0:
            self.blocked_entries += 1
            return {
                "status": "BLOCKED",
                "reason": "Insufficient capital or risk budget"
            }

        position = {
            "symbol": symbol,
            "exchange": exchange,
            "entry": entry_price,
            "stop": stop_loss,
            "target": target,
            "quantity": quantity,
            "entry_time": timestamp
        }

        self.positions[symbol] = position

        self.risk_guard.record_entry()

        return {
            "status": "PAPER_POSITION_OPENED",
            **position
        }

    def close_position(
        self,
        symbol,
        exit_price,
        timestamp,
        reason="MANUAL_EXIT"
    ):

        symbol = symbol.upper()

        if symbol not in self.positions:
            return {"status": "NO_OPEN_POSITION"}

        position = self.positions.pop(symbol)

        cost_result = self._calculate_position_costs(
            entry_price=position["entry"],
            exit_price=exit_price,
            quantity=position["quantity"],
            exchange=position.get("exchange", "NSE")
        )

        net_pnl = cost_result["net_pnl"]

        self.balance += net_pnl

        self.risk_guard.record_trade(net_pnl)

        trade = {
            **position,
            "exit": exit_price,
            "exit_time": timestamp,
            "reason": reason,
            "gross_pnl": cost_result["gross_pnl"],
            "total_cost": cost_result["total_cost"],
            "net_pnl": net_pnl,
            "cost_breakdown": cost_result
        }

        self.trade_history.append(trade)

        return {
            "status": "PAPER_POSITION_CLOSED",
            **trade
        }

    def close_all_positions(
        self,
        prices,
        timestamp,
        reason="PORTFOLIO_EXIT"
    ):

        results = []

        for symbol in list(self.positions.keys()):

            if symbol not in prices:
                continue

            results.append(
                self.close_position(
                    symbol,
                    prices[symbol],
                    timestamp,
                    reason
                )
            )

        return results

    def get_report(self, prices=None):

        prices = prices or {}

        unrealized = self.calculate_unrealized_pnl(prices)

        return {
            "initial_capital": self.initial_capital,
            "balance": self.balance,
            "committed_capital": self.committed_capital,
            "unrealized_pnl": unrealized,
            "equity": (
                self.balance
                + self.committed_capital
                + unrealized
            ),
            "open_positions": len(self.positions),
            "completed_trades": len(self.trade_history),
            "blocked_entries": self.blocked_entries,
            "risk_report": self.risk_guard.get_report(unrealized)
        }
