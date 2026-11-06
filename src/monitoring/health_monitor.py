"""
Stage 26 – Health Monitor
Checks system health: last candle age, open position count, and memory usage.
"""

import time
from datetime import datetime


class HealthMonitor:
    """
    Lightweight health checker for the paper-trading system.

    Records various system metrics and exposes a status report.

    Parameters
    ----------
    max_candle_age_seconds  : int – alert if last candle is older than this
    max_open_positions      : int – alert if open positions exceed this
    """

    def __init__(
        self,
        max_candle_age_seconds: int = 300,   # 5 minutes = one candle
        max_open_positions: int = 10
    ):
        if max_candle_age_seconds <= 0:
            raise ValueError("max_candle_age_seconds must be positive")
        if max_open_positions <= 0:
            raise ValueError("max_open_positions must be positive")

        self.max_candle_age_seconds = max_candle_age_seconds
        self.max_open_positions = max_open_positions

        self._last_candle_time = None
        self._start_time = time.time()

    def record_candle(self, timestamp=None):
        """Call each time a new market candle is processed."""
        self._last_candle_time = timestamp or datetime.now()

    def check_candle_age(self) -> dict:
        """Return candle-age health status."""
        if self._last_candle_time is None:
            return {
                "ok": False,
                "issue": "No candle received yet",
                "age_seconds": None
            }

        if isinstance(self._last_candle_time, datetime):
            age = (datetime.now() - self._last_candle_time).total_seconds()
        else:
            age = 0.0

        ok = age <= self.max_candle_age_seconds
        return {
            "ok": ok,
            "age_seconds": round(age, 1),
            "issue": None if ok else f"Candle stale: {age:.0f}s > {self.max_candle_age_seconds}s"
        }

    def check_positions(self, open_positions: int) -> dict:
        """Return position-count health status."""
        ok = open_positions <= self.max_open_positions
        return {
            "ok": ok,
            "open_positions": open_positions,
            "issue": (
                None if ok
                else f"Too many open positions: {open_positions} > {self.max_open_positions}"
            )
        }

    def check_memory(self) -> dict:
        """Return basic process memory information if psutil is available."""
        try:
            import psutil
            process = psutil.Process()
            mem_mb = process.memory_info().rss / 1024 / 1024
            return {"ok": True, "memory_mb": round(mem_mb, 1), "issue": None}
        except ImportError:
            return {"ok": True, "memory_mb": None, "issue": "psutil not installed"}

    def get_report(self, open_positions: int = 0) -> dict:
        """Return a combined health report."""
        candle_check   = self.check_candle_age()
        position_check = self.check_positions(open_positions)
        memory_check   = self.check_memory()

        issues = [
            c["issue"]
            for c in [candle_check, position_check, memory_check]
            if c["issue"]
        ]

        uptime_seconds = round(time.time() - self._start_time, 1)

        return {
            "healthy": not issues,
            "issues": issues,
            "uptime_seconds": uptime_seconds,
            "candle": candle_check,
            "positions": position_check,
            "memory": memory_check,
        }
