"""
Stage 27 – Slippage Sensitivity Sweep
Reruns a strategy across a range of slippage values and reports how
net P&L and trade count vary with slippage.
"""

import pandas as pd
from typing import Callable, List


def run_slippage_sweep(
    df: pd.DataFrame,
    strategy_fn: Callable,
    slippage_values: List[float]
) -> pd.DataFrame:
    """
    Run *strategy_fn* for each slippage value in *slippage_values*.

    *strategy_fn* signature: strategy_fn(df, slippage_per_share) → dict
      The dict must contain at least: 'net_pnl', 'total_trades'.

    Returns
    -------
    DataFrame with columns: slippage, net_pnl, total_trades,
                            pnl_vs_zero_slip (% change from baseline)
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    if not slippage_values:
        raise ValueError("slippage_values must not be empty")

    for s in slippage_values:
        if s < 0:
            raise ValueError(f"Slippage cannot be negative: {s}")

    rows = []
    baseline_pnl = None

    for slip in slippage_values:
        try:
            result = strategy_fn(df, slip)
        except Exception as exc:
            result = {"net_pnl": 0, "total_trades": 0, "error": str(exc)}

        net_pnl = result.get("net_pnl", 0)

        if baseline_pnl is None:
            baseline_pnl = net_pnl

        pnl_change = (
            ((net_pnl - baseline_pnl) / abs(baseline_pnl) * 100)
            if baseline_pnl != 0 else 0.0
        )

        rows.append({
            "slippage":          slip,
            "net_pnl":           round(net_pnl, 2),
            "total_trades":      result.get("total_trades", 0),
            "pnl_vs_zero_slip":  round(pnl_change, 2),
        })

    return pd.DataFrame(rows)
