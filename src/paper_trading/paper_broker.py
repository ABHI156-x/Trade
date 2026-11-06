
from src.risk.risk_manager import calculate_position_size


class PaperBroker:

    def __init__(self, risk_guard):
        self.risk_guard = risk_guard
        self.position = None
        self.trade_history = []

    def buy(self, symbol, entry, stop_loss, target, capital,
            risk_per_trade=100):

        if self.position is not None:
            return {"status": "BLOCKED", "reason": "A position is already open."}

        allowed, message = self.risk_guard.can_take_trade()

        if not allowed:
            return {"status": "BLOCKED", "reason": message}

        result = calculate_position_size(
            entry_price=entry,
            stop_loss=stop_loss,
            target_price=target,
            available_capital=capital,
            risk_per_trade=risk_per_trade,
            daily_loss=self.risk_guard.daily_loss(),
            max_daily_loss=self.risk_guard.max_daily_loss
        )

        if result["status"] != "APPROVED_FOR_PAPER_TEST":
            return result

        self.position = {
            "symbol": symbol,
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "quantity": result["quantity"]
        }

        return {
            "status": "PAPER_POSITION_OPENED",
            **self.position
        }
    
    def monitor_candle(self, high, low):

        if self.position is None:
            return {
                "status": "NO_OPEN_POSITION"
            }

        trade = self.position

        stop_hit = low <= trade["stop_loss"]
        target_hit = high >= trade["target"]

        # Conservative assumption:
        # If both levels are reached in one candle,
        # assume stop-loss happened first.
        if stop_hit:
            return self.sell(trade["stop_loss"])

        if target_hit:
            return self.sell(trade["target"])

        return {
            "status": "POSITION_HOLDING",
            "symbol": trade["symbol"],
            "message": "Stop-loss and target not reached."
        }


    def sell(self, exit_price):

        if self.position is None:
            return {"status": "BLOCKED", "reason": "No open position."}

        if exit_price <= 0:
            return {"status": "BLOCKED", "reason": "Invalid exit price."}

        trade = self.position

        pnl = (exit_price - trade["entry"]) * trade["quantity"]

        self.risk_guard.register_trade(pnl)

        completed_trade = {
            **trade,
            "exit_price": exit_price,
            "pnl": round(pnl, 2)
        }

        self.trade_history.append(completed_trade)
        self.position = None

        return {
            "status": "PAPER_POSITION_CLOSED",
            **completed_trade
        }
