
import math
import pandas as pd

from src.analysis.market_regime import classify_regimes_by_symbol

from src.backtesting.strategy_comparison import (
    compare_ema_strategies,
    calculate_risk_adjusted_score,
    MINIMUM_TRADES_FOR_CONFIDENCE
)


def _calculate_regime_metrics(trades, regime, initial_capital):
    """Calculate performance metrics for one regime."""

    regime_trades = [
        trade for trade in trades
        if trade["market_regime"] == regime
    ]

    regime_trades.sort(
        key=lambda trade: (
            trade["exit_time"],
            trade["entry_time"],
            trade["symbol"]
        )
    )

    winners = [
        trade for trade in regime_trades
        if trade["net_pnl"] > 0
    ]

    losers = [
        trade for trade in regime_trades
        if trade["net_pnl"] < 0
    ]

    breakeven = [
        trade for trade in regime_trades
        if trade["net_pnl"] == 0
    ]

    total_trades = len(regime_trades)

    net_pnl = sum(
        trade["net_pnl"]
        for trade in regime_trades
    )

    total_costs = sum(
        trade["total_cost"]
        for trade in regime_trades
    )

    winning_pnl = sum(
        trade["net_pnl"]
        for trade in winners
    )

    losing_pnl = abs(sum(
        trade["net_pnl"]
        for trade in losers
    ))

    traded_value = sum(
        trade["entry"] * trade["quantity"]
        for trade in regime_trades
    )

    # Regime-level realized equity curve.
    # This is not the full portfolio equity curve.
    running_equity = float(initial_capital)
    peak_equity = running_equity
    max_drawdown_amount = 0.0

    for trade in regime_trades:
        running_equity += trade["net_pnl"]

        peak_equity = max(
            peak_equity,
            running_equity
        )

        drawdown = peak_equity - running_equity

        max_drawdown_amount = max(
            max_drawdown_amount,
            drawdown
        )

    max_drawdown_percent = (
        max_drawdown_amount / initial_capital * 100
    )

    return_percent = (
        net_pnl / traded_value * 100
        if traded_value > 0 else 0
    )

    risk_adjusted_score = calculate_risk_adjusted_score(
        return_percent=return_percent,
        max_drawdown_percent=max_drawdown_percent,
        total_trades=total_trades
    )

    return {
        "market_regime": regime,
        "total_trades": total_trades,
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "breakeven_trades": len(breakeven),
        "net_pnl": round(net_pnl, 2),
        "total_costs": round(total_costs, 2),
        "win_rate": round(
            len(winners) / total_trades * 100,
            2
        ) if total_trades else 0,
        "average_net_pnl": round(
            net_pnl / total_trades,
            2
        ) if total_trades else 0,
        "return_on_traded_value_percent": round(
            return_percent,
            4
        ),
        "max_drawdown_amount": round(
            max_drawdown_amount,
            2
        ),
        "max_drawdown_percent": round(
            max_drawdown_percent,
            4
        ),
        "profit_factor": round(
            winning_pnl / losing_pnl,
            2
        ) if losing_pnl > 0 else (
            None if winning_pnl == 0 else None
        ),
        "risk_adjusted_score": risk_adjusted_score,
        "sample_status": (
            "Sufficient sample"
            if total_trades >= MINIMUM_TRADES_FOR_CONFIDENCE
            else "Insufficient sample"
        )
    }


def compare_strategies_by_market_regime(
    df,
    strategy_configs=None,
    backtest_kwargs=None,
    regime_kwargs=None
):
    """
    Compare EMA strategies separately within each market regime.

    1. Classify each symbol's market regime.
    2. Run each strategy on the complete chronological dataset.
    3. Match each completed trade to its entry regime.
    4. Aggregate and rank strategies separately by regime.

    Regime rankings use realized closed-trade results.
    """

    if (
        df is None
        or not isinstance(df, pd.DataFrame)
        or df.empty
    ):
        raise ValueError("No market data available.")

    required_columns = {
        "timestamp",
        "symbol",
        "high",
        "low",
        "close"
    }

    if not required_columns.issubset(df.columns):
        raise ValueError("Missing required market data columns.")

    if backtest_kwargs is None:
        backtest_kwargs = {}

    if regime_kwargs is None:
        regime_kwargs = {}

    if not isinstance(backtest_kwargs, dict):
        raise ValueError("Backtest settings must be a dictionary.")

    if not isinstance(regime_kwargs, dict):
        raise ValueError("Regime settings must be a dictionary.")

    backtest_kwargs = dict(backtest_kwargs)
    regime_kwargs = dict(regime_kwargs)

    reserved_parameters = {
        "df",
        "fast_ema_period",
        "slow_ema_period"
    }

    if reserved_parameters.intersection(backtest_kwargs):
        raise ValueError(
            "Do not override dataframe or strategy EMA parameters."
        )

    if not isinstance(df, pd.DataFrame):
        raise ValueError("Invalid market data.")

    working_df = df.copy()

    working_df["timestamp"] = pd.to_datetime(
        working_df["timestamp"],
        errors="coerce"
    )

    if working_df["timestamp"].isna().any():
        raise ValueError("Invalid timestamps found.")

    if working_df["symbol"].isna().any():
        raise ValueError("Invalid symbols found.")

    working_df["symbol"] = (
        working_df["symbol"].astype(str).str.strip()
    )

    if (working_df["symbol"] == "").any():
        raise ValueError("Empty symbols found.")

    if working_df.duplicated(
        ["timestamp", "symbol"]
    ).any():
        raise ValueError("Duplicate timestamp and symbol combinations.")

    working_df = working_df.sort_values(
        ["timestamp", "symbol"]
    ).reset_index(drop=True)

    # Classify regimes independently for each symbol.
    classified_df = classify_regimes_by_symbol(
        working_df,
        **regime_kwargs
    )

    if "MARKET_REGIME" not in classified_df.columns:
        raise ValueError("Market regime classification failed.")

    if classified_df["MARKET_REGIME"].isna().any():
        raise ValueError("Missing market regime classifications.")

    # Run all strategies on the complete data.
    # Do not filter candles by regime before backtesting.
    comparison_result = compare_ema_strategies(
        classified_df,
        strategy_configs=strategy_configs,
        backtest_kwargs=backtest_kwargs
    )

    regimes = sorted(
        classified_df["MARKET_REGIME"].unique().tolist()
    )

    # Include UNKNOWN to make missing matches visible.
    if "UNKNOWN" not in regimes:
        regimes.append("UNKNOWN")

    initial_capital = backtest_kwargs.get(
        "initial_capital",
        10000
    )

    if (
        not isinstance(initial_capital, (int, float))
        or isinstance(initial_capital, bool)
        or not math.isfinite(initial_capital)
        or initial_capital <= 0
    ):
        raise ValueError("Initial capital must be positive and finite.")

    regime_rankings = {
        regime: []
        for regime in regimes
    }

    strategy_details = []

    for strategy_result in comparison_result["strategy_reports"]:

        strategy_name = strategy_result["strategy"]
        backtest_report = strategy_result["report"]

        trades = backtest_report.get("trade_history", [])

        if not isinstance(trades, list):
            raise ValueError("Invalid strategy trade history.")

        regime_lookup = classified_df.set_index(
            ["timestamp", "symbol"]
        )["MARKET_REGIME"]

        matched_trades = []

        for trade in trades:

            if not isinstance(trade, dict):
                raise ValueError("Invalid trade record.")

            required_trade_fields = {
                "symbol",
                "entry_time",
                "exit_time",
                "entry",
                "quantity",
                "net_pnl",
                "total_cost"
            }

            if not required_trade_fields.issubset(trade):
                raise ValueError("Missing trade fields.")

            entry_time = pd.to_datetime(
                trade["entry_time"],
                errors="coerce"
            )

            exit_time = pd.to_datetime(
                trade["exit_time"],
                errors="coerce"
            )

            if pd.isna(entry_time) or pd.isna(exit_time):
                raise ValueError("Invalid trade timestamps.")

            if exit_time < entry_time:
                raise ValueError("Trade exit precedes entry.")

            symbol = str(trade["symbol"]).strip()

            if not symbol:
                raise ValueError("Invalid trade symbol.")

            numeric_values = [
                trade["entry"],
                trade["quantity"],
                trade["net_pnl"],
                trade["total_cost"]
            ]

            if not all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                for value in numeric_values
            ):
                raise ValueError("Invalid trade numeric values.")

            entry, quantity, net_pnl, total_cost = numeric_values

            if entry <= 0 or quantity <= 0 or total_cost < 0:
                raise ValueError("Invalid trade price, quantity or cost.")

            regime = regime_lookup.get(
                (entry_time, symbol),
                "UNKNOWN"
            )

            matched_trades.append({
                "symbol": symbol,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry": entry,
                "quantity": quantity,
                "net_pnl": net_pnl,
                "total_cost": total_cost,
                "market_regime": regime
            })

        strategy_regime_results = []

        for regime in regimes:

            metrics = _calculate_regime_metrics(
                matched_trades,
                regime,
                initial_capital
            )

            metrics["strategy"] = strategy_name

            regime_rankings[regime].append(metrics)
            strategy_regime_results.append(metrics)

        strategy_details.append({
            "strategy": strategy_name,
            "fast_period": strategy_result["fast_period"],
            "slow_period": strategy_result["slow_period"],
            "overall_report": backtest_report,
            "regime_performance": strategy_regime_results
        })

    # Rank strategies separately inside each regime.
    for regime, ranking in regime_rankings.items():

        ranking.sort(
            key=lambda item: (
                item["risk_adjusted_score"],
                item["net_pnl"]
            ),
            reverse=True
        )

        for rank, item in enumerate(ranking, start=1):
            item["rank"] = rank

    best_strategy_by_regime = {}

    for regime, ranking in regime_rankings.items():

        traded_strategies = [
            item for item in ranking
            if item["total_trades"] > 0
        ]

        best_strategy_by_regime[regime] = (
            traded_strategies[0]
            if traded_strategies else None
        )

    return {
        "total_strategies": comparison_result["total_strategies"],
        "regimes_analyzed": regimes,
        "best_strategy_by_regime": best_strategy_by_regime,
        "regime_rankings": regime_rankings,
        "strategy_details": strategy_details,
        "initial_capital": float(initial_capital),
        "minimum_trades_for_confidence": (
            MINIMUM_TRADES_FOR_CONFIDENCE
        ),
        "note": (
            "Regime metrics use the market regime at trade entry. "
            "Drawdown is calculated from closed trades within each "
            "regime and is not the full portfolio drawdown."
        )
    }
