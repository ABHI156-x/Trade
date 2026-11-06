"""
Stage 24 – Paper Trading Dashboard
Terminal dashboard: prints equity, open positions, P&L, risk state.
"""

from src.dashboard.equity_chart import render_ascii_equity_curve


class PaperTradingDashboard:
    """
    Renders a formatted terminal snapshot of the paper-trading state.

    Usage
    -----
    dashboard = PaperTradingDashboard()
    dashboard.update_equity(current_equity)  # call each bar
    dashboard.render(broker_report, risk_report)
    """

    def __init__(self):
        self.equity_history = []

    def update_equity(self, equity: float):
        """Append the latest equity value to the history."""
        self.equity_history.append(equity)

    def render(self, broker_report: dict, risk_report: dict = None) -> str:
        """
        Build and print a dashboard snapshot.

        Parameters
        ----------
        broker_report : dict returned by PortfolioPaperBroker.get_report()
        risk_report   : dict returned by DailyRiskGuard.get_report()  (optional)

        Returns
        -------
        The rendered string (also printed to stdout).
        """
        lines = []
        W = 62

        def hr(char="─"):
            return char * W

        lines.append("")
        lines.append("╔" + "═" * (W - 2) + "╗")
        lines.append("║" + "  INDIAN DAY TRADER – PAPER TRADING DASHBOARD  ".center(W - 2) + "║")
        lines.append("╚" + "═" * (W - 2) + "╝")

        # Equity summary
        initial  = broker_report.get("initial_capital", 0)
        balance  = broker_report.get("balance", 0)
        equity   = broker_report.get("equity", balance)
        unreal   = broker_report.get("unrealized_pnl", 0)
        realized = balance - initial

        lines.append(hr())
        lines.append(f"  Initial Capital  : ₹{initial:>12,.2f}")
        lines.append(f"  Cash Balance     : ₹{balance:>12,.2f}")
        lines.append(f"  Portfolio Equity : ₹{equity:>12,.2f}")
        _sign = "+" if realized >= 0 else ""
        lines.append(f"  Realized P&L     : {_sign}₹{realized:>11,.2f}")
        _sign = "+" if unreal >= 0 else ""
        lines.append(f"  Unrealized P&L   : {_sign}₹{unreal:>11,.2f}")

        # Open positions
        open_pos = broker_report.get("open_positions", 0)
        closed   = broker_report.get("completed_trades", 0)
        blocked  = broker_report.get("blocked_entries", 0)
        lines.append(hr())
        lines.append(f"  Open Positions   : {open_pos}")
        lines.append(f"  Completed Trades : {closed}")
        lines.append(f"  Blocked Entries  : {blocked}")

        # Daily risk
        if risk_report:
            lines.append(hr())
            lines.append("  DAILY RISK GUARD")
            lines.append(
                f"  Trades Taken     : "
                f"{risk_report.get('trades_taken', '-')} / "
                f"{risk_report.get('trades_taken', 0) + risk_report.get('remaining_trades', 0)}"
            )
            daily_loss = risk_report.get("daily_loss", 0)
            loss_limit = risk_report.get("remaining_loss_limit", 0) + daily_loss
            lines.append(
                f"  Daily Loss       : ₹{daily_loss:>10,.2f}  "
                f"(limit ₹{loss_limit:,.0f})"
            )
            lines.append(
                f"  Remaining Budget : ₹{risk_report.get('remaining_loss_limit', 0):>10,.2f}"
            )

        # Equity curve sparkline
        if len(self.equity_history) >= 2:
            lines.append(hr())
            lines.append(render_ascii_equity_curve(self.equity_history, width=56))

        lines.append(hr("─"))
        lines.append("")

        output = "\n".join(lines)
        print(output)
        return output
