"""
Stage 27 – Tests for WalkForwardBacktester, slippage_sensitivity, MonteCarloSimulator
"""

import pytest
import pandas as pd
from src.backtesting.out_of_sample_backtester import WalkForwardBacktester
from src.backtesting.slippage_sensitivity import run_slippage_sweep
from src.backtesting.monte_carlo import MonteCarloSimulator


# ------------------------------------------------------------------ Helpers

def _make_df(n=100):
    ts = pd.date_range("2024-01-02 09:15", periods=n, freq="5min")
    return pd.DataFrame({
        "timestamp": ts,
        "symbol": "TEST",
        "open":   100.0,
        "high":   101.0,
        "low":     99.0,
        "close":  100.5,
        "volume":   500,
    })


def _simple_strategy(df):
    """Dummy strategy: returns a fixed result."""
    return {
        "net_pnl": len(df) * 0.5,
        "total_trades": max(1, len(df) // 10),
        "initial_capital": 10000,
        "final_capital": 10000 + len(df) * 0.5,
    }


def _slip_strategy(df, slippage_per_share):
    """Dummy strategy that subtracts slippage impact."""
    pnl = len(df) * 0.5 - slippage_per_share * 10
    return {"net_pnl": pnl, "total_trades": 5}


# ------------------------------------------------------------------ WalkForward

class TestWalkForwardBacktester:

    def test_returns_folds_and_aggregate(self):
        df = _make_df(100)
        wf = WalkForwardBacktester(n_splits=4)
        result = wf.run(df, _simple_strategy)
        assert "folds" in result
        assert "aggregate" in result

    def test_fold_count(self):
        df = _make_df(100)
        wf = WalkForwardBacktester(n_splits=4)
        result = wf.run(df, _simple_strategy)
        assert len(result["folds"]) >= 1

    def test_aggregate_has_mean_pnl(self):
        df = _make_df(100)
        wf = WalkForwardBacktester(n_splits=4)
        result = wf.run(df, _simple_strategy)
        assert "mean_pnl" in result["aggregate"]
        assert "consistency" in result["aggregate"]

    def test_invalid_n_splits_raises(self):
        with pytest.raises(ValueError):
            WalkForwardBacktester(n_splits=1)

    def test_invalid_test_ratio_raises(self):
        with pytest.raises(ValueError):
            WalkForwardBacktester(test_ratio=1.5)

    def test_empty_df_raises(self):
        wf = WalkForwardBacktester()
        with pytest.raises(ValueError):
            wf.run(pd.DataFrame(), _simple_strategy)


# ------------------------------------------------------------------ Slippage sweep

class TestSlippageSensitivity:

    def test_returns_dataframe(self):
        df = _make_df(50)
        result = run_slippage_sweep(df, _slip_strategy, [0, 0.05, 0.10])
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == [
            "slippage", "net_pnl", "total_trades", "pnl_vs_zero_slip"
        ]

    def test_row_count_matches_slippage_values(self):
        df = _make_df(50)
        result = run_slippage_sweep(df, _slip_strategy, [0, 0.05, 0.10, 0.20])
        assert len(result) == 4

    def test_higher_slippage_lower_pnl(self):
        df = _make_df(50)
        result = run_slippage_sweep(df, _slip_strategy, [0, 0.10, 0.50])
        pnls = result["net_pnl"].tolist()
        assert pnls[0] >= pnls[-1]    # zero slip >= high slip

    def test_negative_slippage_raises(self):
        df = _make_df(50)
        with pytest.raises(ValueError):
            run_slippage_sweep(df, _slip_strategy, [-0.05])

    def test_empty_slippage_values_raises(self):
        df = _make_df(50)
        with pytest.raises(ValueError):
            run_slippage_sweep(df, _slip_strategy, [])


# ------------------------------------------------------------------ Monte Carlo

class TestMonteCarloSimulator:

    def test_returns_expected_keys(self):
        mc = MonteCarloSimulator(n_simulations=100, seed=42)
        result = mc.run([100, -50, 200, -30, 80], initial_capital=10000)
        assert "final_equity" in result
        assert "max_drawdown" in result
        assert "probability_profit" in result

    def test_percentile_ordering(self):
        mc = MonteCarloSimulator(n_simulations=500, seed=0)
        result = mc.run([100, -50, 200, -30, 80] * 5, initial_capital=10000)
        fe = result["final_equity"]
        assert fe["p5"] <= fe["p50"] <= fe["p95"]

    def test_probability_profit_range(self):
        mc = MonteCarloSimulator(n_simulations=200, seed=1)
        result = mc.run([100, 200, 150], initial_capital=10000)
        assert 0 <= result["probability_profit"] <= 1

    def test_empty_trades_raises(self):
        mc = MonteCarloSimulator()
        with pytest.raises(ValueError):
            mc.run([], initial_capital=10000)

    def test_invalid_capital_raises(self):
        mc = MonteCarloSimulator()
        with pytest.raises(ValueError):
            mc.run([100], initial_capital=0)

    def test_negative_n_simulations_raises(self):
        with pytest.raises(ValueError):
            MonteCarloSimulator(n_simulations=0)
