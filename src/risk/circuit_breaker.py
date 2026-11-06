"""
Stage 23 – Index-level Circuit Breaker
Mirrors SEBI/NSE rules: trading halts at 10 %, 15 %, 20 % index falls.
"""


# SEBI-mandated halt durations (in minutes) by threshold and time-of-day
# Reference: SEBI circular on Market-Wide Circuit Breakers
_SEBI_HALTS = {
    0.10: {"before_13:00": 45, "13:00_to_14:30": 15, "after_14:30": 0},
    0.15: {"before_13:00": 105, "13:00_to_14:30": 45, "after_14:30": 0},
    0.20: {"all": "remainder_of_day"},
}


class IndexCircuitBreaker:
    """
    Simulates NSE/BSE Market-Wide Circuit Breakers (MWCB).

    Parameters
    ----------
    index_open_price : float – Nifty / Sensex opening price for the day
    thresholds       : tuple of fractions, default (0.10, 0.15, 0.20)
    """

    def __init__(
        self,
        index_open_price: float,
        thresholds: tuple = (0.10, 0.15, 0.20)
    ):
        if index_open_price <= 0:
            raise ValueError("index_open_price must be positive")

        if not thresholds:
            raise ValueError("At least one threshold is required")

        for t in thresholds:
            if not 0 < t < 1:
                raise ValueError(f"Threshold {t} must be between 0 and 1")

        self.index_open_price = index_open_price
        self.thresholds = sorted(thresholds)
        self.triggered_thresholds = set()

    def check(self, current_price: float) -> dict:
        """
        Evaluate current index price against circuit-breaker thresholds.

        Returns
        -------
        dict with keys:
          - triggered (bool)
          - threshold (float or None)
          - fall_percent (float)
          - halt_minutes (int or str)  – "remainder_of_day" for 20 % breach
          - message (str)
        """
        if current_price <= 0:
            raise ValueError("current_price must be positive")

        fall = (self.index_open_price - current_price) / self.index_open_price
        fall = max(fall, 0.0)   # only downward moves trigger MWCB

        highest_breach = None

        for t in reversed(self.thresholds):     # check worst first
            if fall >= t:
                highest_breach = t
                break

        if highest_breach is None:
            return {
                "triggered": False,
                "threshold": None,
                "fall_percent": round(fall * 100, 4),
                "halt_minutes": 0,
                "message": f"No circuit breaker. Fall: {fall*100:.2f}%"
            }

        if highest_breach == 0.20:
            halt = "remainder_of_day"
        elif highest_breach == 0.15:
            halt = 105
        else:
            halt = 45

        self.triggered_thresholds.add(highest_breach)

        return {
            "triggered": True,
            "threshold": highest_breach,
            "fall_percent": round(fall * 100, 4),
            "halt_minutes": halt,
            "message": (
                f"CIRCUIT BREAKER at {highest_breach*100:.0f}% "
                f"(fall {fall*100:.2f}%). "
                f"Halt: {halt} min"
            )
        }

    def is_halted(self, current_price: float) -> bool:
        """Convenience: True if any circuit-breaker threshold has been breached."""
        return self.check(current_price)["triggered"]

    def reset_day(self, new_open_price: float):
        """Reset for a new trading day."""
        if new_open_price <= 0:
            raise ValueError("new_open_price must be positive")
        self.index_open_price = new_open_price
        self.triggered_thresholds.clear()
