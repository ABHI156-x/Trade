"""
Stage 27 – Monte Carlo Simulator
Shuffles historical trade P&L sequences to build confidence intervals
for final equity and maximum drawdown.
"""

import random
from typing import List, Dict


class MonteCarloSimulator:
    """
    Simulate portfolio outcomes by randomly reordering observed trade P&Ls.

    Parameters
    ----------
    n_simulations : int – number of Monte Carlo paths to generate
    seed          : int or None – random seed for reproducibility
    """

    def __init__(self, n_simulations: int = 1000, seed: int = None):
        if n_simulations < 1:
            raise ValueError("n_simulations must be >= 1")

        self.n_simulations = n_simulations
        self._rng = random.Random(seed)

    def _run_single(
        self,
        pnl_sequence: List[float],
        initial_capital: float
    ):
        """Simulate one shuffled equity path. Return (final_equity, max_drawdown)."""
        equity   = initial_capital
        peak     = initial_capital
        max_dd   = 0.0

        shuffled = list(pnl_sequence)
        self._rng.shuffle(shuffled)

        for pnl in shuffled:
            equity += pnl
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd

        return equity, max_dd

    def run(
        self,
        trade_pnls: List[float],
        initial_capital: float = 10000
    ) -> Dict:
        """
        Run Monte Carlo simulation over *trade_pnls*.

        Parameters
        ----------
        trade_pnls      : list of per-trade net P&Ls from historical backtest
        initial_capital : starting portfolio value

        Returns
        -------
        dict with:
          - simulations       : n_simulations
          - initial_capital   : float
          - final_equity      : {p5, p50, p95}   (5th / 50th / 95th percentile)
          - max_drawdown      : {p5, p50, p95}
          - probability_profit: fraction of paths ending above initial_capital
        """
        if not trade_pnls:
            raise ValueError("trade_pnls must not be empty")

        if initial_capital <= 0:
            raise ValueError("initial_capital must be positive")

        equities   = []
        drawdowns  = []

        for _ in range(self.n_simulations):
            eq, dd = self._run_single(trade_pnls, initial_capital)
            equities.append(eq)
            drawdowns.append(dd)

        equities.sort()
        drawdowns.sort()

        def percentile(data, pct):
            idx = int(len(data) * pct / 100)
            idx = max(0, min(idx, len(data) - 1))
            return round(data[idx], 2)

        prob_profit = sum(1 for e in equities if e > initial_capital) / len(equities)

        return {
            "simulations":        self.n_simulations,
            "initial_capital":    initial_capital,
            "final_equity": {
                "p5":  percentile(equities, 5),
                "p50": percentile(equities, 50),
                "p95": percentile(equities, 95),
            },
            "max_drawdown": {
                "p5":  percentile(drawdowns, 5),
                "p50": percentile(drawdowns, 50),
                "p95": percentile(drawdowns, 95),
            },
            "probability_profit": round(prob_profit, 4),
        }
