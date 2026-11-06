
class PortfolioRiskGuard:

    def __init__(self, max_daily_loss=500, max_trades=3):

        if max_daily_loss <= 0 or max_trades <= 0:
            raise ValueError("Risk limits must be positive.")

        self.max_daily_loss = max_daily_loss
        self.max_trades = max_trades

        self.reset()

    def reset(self):

        self.realized_pnl = 0.0
        self.trades_taken = 0

    def daily_pnl(self, unrealized_pnl=0):

        return self.realized_pnl + unrealized_pnl

    def daily_loss(self, unrealized_pnl=0):

        return max(0.0, -self.daily_pnl(unrealized_pnl))

    def can_take_trade(self, unrealized_pnl=0):

        if self.daily_loss(unrealized_pnl) >= self.max_daily_loss:
            return False, "Portfolio daily loss limit reached."

        if self.trades_taken >= self.max_trades:
            return False, "Portfolio daily trade limit reached."

        return True, "Trade allowed."

    def record_entry(self):

        self.trades_taken += 1

    def record_trade(self, pnl):

        self.realized_pnl += pnl

    def get_report(self, unrealized_pnl=0):

        return {
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "daily_pnl": round(
                self.daily_pnl(unrealized_pnl), 2
            ),
            "daily_loss": round(
                self.daily_loss(unrealized_pnl), 2
            ),
            "trades_taken": self.trades_taken,
            "remaining_trades": max(
                0, self.max_trades - self.trades_taken
            ),
            "remaining_loss_limit": round(
                max(
                    0,
                    self.max_daily_loss - self.daily_loss(unrealized_pnl)
                ),
                2
            )
        }
