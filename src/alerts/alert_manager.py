"""
Stage 25 – Alert Manager
Central dispatcher for signal, risk, and trade alerts.
Sends to all registered notifiers (console, email, etc.).
"""

from typing import List
from datetime import datetime


class AlertManager:
    """
    Dispatches alerts to a list of notifiers.

    Parameters
    ----------
    notifiers : list of objects with a .send(message, level) method
    """

    def __init__(self, notifiers: List = None):
        self.notifiers = notifiers or []
        self.history = []

    def _dispatch(self, message: str, level: str = "INFO"):
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "level": level.upper(),
            "message": message,
        }
        self.history.append(entry)

        for notifier in self.notifiers:
            try:
                notifier.send(message, level)
            except Exception as exc:    # noqa: BLE001
                print(f"[AlertManager] Notifier error: {exc}")

        return entry

    # ------------------------------------------------------------------ Public API

    def signal_alert(self, symbol: str, signal_type: str, details: str = ""):
        """Fire a trading signal alert."""
        msg = f"SIGNAL | {symbol} | {signal_type}"
        if details:
            msg += f" | {details}"
        return self._dispatch(msg, level="INFO")

    def risk_alert(self, reason: str):
        """Fire a risk/circuit-breaker alert."""
        msg = f"RISK ALERT | {reason}"
        return self._dispatch(msg, level="WARNING")

    def trade_alert(self, trade: dict):
        """Fire a trade execution alert."""
        symbol    = trade.get("symbol", "?")
        action    = "OPEN" if "entry" in trade and "exit" not in trade else "CLOSE"
        net_pnl   = trade.get("net_pnl", "")
        pnl_str   = f" | P&L: ₹{net_pnl:.2f}" if isinstance(net_pnl, (int, float)) else ""
        msg = f"TRADE {action} | {symbol}{pnl_str}"
        return self._dispatch(msg, level="INFO")

    def system_alert(self, message: str):
        """Fire a general system / error alert."""
        return self._dispatch(message, level="ERROR")

    def get_history(self, level: str = None) -> List[dict]:
        """Return alert history, optionally filtered by level."""
        if level is None:
            return list(self.history)
        level = level.upper()
        return [e for e in self.history if e["level"] == level]
