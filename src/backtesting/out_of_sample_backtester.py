"""
Stage 27 – Walk-Forward / Out-of-Sample Backtester
Splits data chronologically into N folds; trains on in-sample, evaluates
on out-of-sample. Returns per-fold and aggregate metrics.
"""

import pandas as pd
from typing import Callable, Dict, List


class WalkForwardBacktester:
    """
    Chronological walk-forward validation for any strategy function.

    Parameters
    ----------
    n_splits   : int – number of train/test folds
    test_ratio : float – fraction of each fold used for out-of-sample test
    """

    def __init__(self, n_splits: int = 5, test_ratio: float = 0.2):
        if n_splits < 2:
            raise ValueError("n_splits must be >= 2")
        if not 0 < test_ratio < 1:
            raise ValueError("test_ratio must be in (0, 1)")

        self.n_splits   = n_splits
        self.test_ratio = test_ratio

    def _make_splits(self, df: pd.DataFrame):
        """Yield (train_df, test_df) tuples."""
        n = len(df)
        fold_size = n // self.n_splits

        for i in range(self.n_splits):
            train_end = fold_size * (i + 1)
            test_end  = min(train_end + int(fold_size * self.test_ratio), n)

            if train_end >= n or test_end > n:
                break

            train = df.iloc[:train_end].copy()
            test  = df.iloc[train_end:test_end].copy()

            if train.empty or test.empty:
                continue

            yield train, test

    def run(
        self,
        df: pd.DataFrame,
        strategy_fn: Callable[[pd.DataFrame], Dict]
    ) -> Dict:
        """
        Run walk-forward validation.

        Parameters
        ----------
        df          : full OHLCV DataFrame sorted by timestamp
        strategy_fn : callable(df) → dict with at least keys:
                      'net_pnl', 'total_trades', 'initial_capital', 'final_capital'

        Returns
        -------
        dict with 'folds' (list of per-fold result dicts) and 'aggregate' metrics
        """
        if df.empty:
            raise ValueError("DataFrame is empty")

        df = df.sort_values("timestamp").reset_index(drop=True)

        folds = []

        for fold_idx, (train_df, test_df) in enumerate(self._make_splits(df)):
            # Strategy trains on train_df (in-sample), evaluated on test_df
            try:
                result = strategy_fn(test_df)
            except Exception as exc:
                result = {"net_pnl": 0, "total_trades": 0, "error": str(exc)}

            folds.append({
                "fold": fold_idx + 1,
                "train_rows": len(train_df),
                "test_rows":  len(test_df),
                **result
            })

        if not folds:
            return {"folds": [], "aggregate": {}}

        pnls   = [f.get("net_pnl", 0) for f in folds]
        trades = [f.get("total_trades", 0) for f in folds]
        wins   = [p > 0 for p in pnls]

        aggregate = {
            "total_folds":    len(folds),
            "winning_folds":  sum(wins),
            "losing_folds":   sum(1 for w in wins if not w),
            "mean_pnl":       round(sum(pnls) / len(pnls), 2),
            "total_pnl":      round(sum(pnls), 2),
            "mean_trades":    round(sum(trades) / len(trades), 1),
            "consistency":    round(sum(wins) / len(wins), 3),
        }

        return {"folds": folds, "aggregate": aggregate}
