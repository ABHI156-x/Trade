"""
Stage 23 – Advanced Risk Guard
Extends DailyRiskGuard with:
  - Maximum portfolio exposure cap (% of capital)
  - Consecutive-loss circuit breaker
  - Per-sector position caps
"""

from src.risk.daily_risk_guard import DailyRiskGuard


class AdvancedRiskGuard(DailyRiskGuard):
    """
    Drop-in replacement for DailyRiskGuard with additional gates.

    Parameters
    ----------
    max_daily_loss        : absolute INR daily loss limit
    max_trades            : max intraday trades
    max_exposure_percent  : 0-1 fraction of total_capital allowed in open positions
    total_capital         : portfolio size for exposure calculation
    max_consecutive_losses: halts new entries after N back-to-back losses
    sector_caps           : dict {sector: max_positions}, e.g. {"BANK": 2}
    """

    def __init__(
        self,
        max_daily_loss=500,
        max_trades=3,
        max_exposure_percent=0.5,
        total_capital=10000,
        max_consecutive_losses=3,
        sector_caps=None
    ):
        super().__init__(
            max_daily_loss=max_daily_loss,
            max_trades=max_trades
        )

        if not 0 < max_exposure_percent <= 1:
            raise ValueError("max_exposure_percent must be in (0, 1]")

        if total_capital <= 0:
            raise ValueError("total_capital must be positive")

        if max_consecutive_losses < 1:
            raise ValueError("max_consecutive_losses must be >= 1")

        self.max_exposure_percent = max_exposure_percent
        self.total_capital = total_capital
        self.max_consecutive_losses = max_consecutive_losses
        self.sector_caps = sector_caps or {}

        # Runtime state
        self._consecutive_losses = 0
        self._sector_counts = {}

    # ----------------------------------------------------------------- reset

    def reset(self):
        super().reset()
        self._consecutive_losses = 0
        self._sector_counts = {}

    # ----------------------------------------------------------------- checks

    def check_exposure(self, current_exposure: float) -> tuple:
        """Return (allowed, reason). current_exposure = total committed capital."""
        limit = self.total_capital * self.max_exposure_percent

        if current_exposure >= limit:
            return (
                False,
                f"Exposure limit reached "
                f"(₹{current_exposure:.0f} >= ₹{limit:.0f})"
            )
        return True, "Exposure OK"

    def check_consecutive_losses(self) -> tuple:
        if self._consecutive_losses >= self.max_consecutive_losses:
            return (
                False,
                f"Circuit breaker: {self._consecutive_losses} consecutive losses"
            )
        return True, "Consecutive-loss OK"

    def check_sector_cap(self, sector: str) -> tuple:
        if sector is None:
            return True, "No sector"

        sector = sector.upper()
        cap = self.sector_caps.get(sector)

        if cap is None:
            return True, "Sector not capped"

        count = self._sector_counts.get(sector, 0)

        if count >= cap:
            return (
                False,
                f"Sector cap reached: {sector} ({count}/{cap})"
            )
        return True, "Sector OK"

    # ----------------------------------------------------------------- override

    def can_take_trade(
        self,
        unrealized_pnl=0,
        current_exposure=0.0,
        sector=None
    ) -> tuple:
        """
        Checks base limits PLUS exposure, consecutive-loss, and sector caps.
        Returns (allowed: bool, reason: str).
        """
        allowed, reason = super().can_take_trade(unrealized_pnl)
        if not allowed:
            return allowed, reason

        allowed, reason = self.check_exposure(current_exposure)
        if not allowed:
            return allowed, reason

        allowed, reason = self.check_consecutive_losses()
        if not allowed:
            return allowed, reason

        allowed, reason = self.check_sector_cap(sector)
        return allowed, reason

    # ----------------------------------------------------------------- record

    def record_trade(self, pnl: float, sector: str = None):
        """Record a completed trade P&L and update streak / sector counts."""
        super().record_trade(pnl)

        if pnl < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

        if sector:
            sector = sector.upper()
            self._sector_counts[sector] = (
                self._sector_counts.get(sector, 0) + 1
            )

        return True, "Trade recorded"

    # ----------------------------------------------------------------- report

    def get_report(self, unrealized_pnl=0):
        base = super().get_report(unrealized_pnl)
        base.update({
            "consecutive_losses": self._consecutive_losses,
            "max_consecutive_losses": self.max_consecutive_losses,
            "sector_counts": dict(self._sector_counts),
        })
        return base
