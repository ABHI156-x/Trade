from pathlib import Path
import math
import pandas as pd

from src.backtesting.portfolio_backtester import (
    run_portfolio_backtest
)

DEFAULT_STRATEGIES = [
    {"name": "EMA 5/20", "fast_period": 5, "slow_period": 20},
    {"name": "EMA 9/21", "fast_period": 9, "slow_period": 21},
    {"name": "EMA 12/26", "fast_period": 12, "slow_period": 26},
    {"name": "EMA 20/50", "fast_period": 20, "slow_period": 50}
]

MINIMUM_TRADES_FOR_CONFIDENCE = 10

def prepare_strategy_data(df, fast_period, slow_period):
    """
    Calculate EMA indicators independently for every symbol.
    """

    if df is None or df.empty:
        raise ValueError("No market data available.")

    if (
        not isinstance(fast_period, int)
        or isinstance(fast_period, bool)
        or not isinstance(slow_period, int)
        or isinstance(slow_period, bool)
        or fast_period <= 0
        or slow_period <= 0
        or fast_period >= slow_period
    ):
        raise ValueError("Invalid EMA periods.")

    if not {"symbol", "timestamp", "close"}.issubset(df.columns):
        raise ValueError("Missing required market data columns.")

    working_df = df.copy()

    working_df["timestamp"] = pd.to_datetime(
        working_df["timestamp"],
        errors="coerce"
    )

    working_df["close"] = pd.to_numeric(
        working_df["close"],
        errors="coerce"
    )

    if working_df["timestamp"].isna().any():
        raise ValueError("Invalid timestamps found.")

    if working_df["close"].isna().any():
        raise ValueError("Invalid closing prices found.")

    if not working_df["close"].map(math.isfinite).all():
        raise ValueError("Closing prices must be finite.")

    if (working_df["close"] <= 0).any():
        raise ValueError("Closing prices must be positive.")

    if working_df["symbol"].isna().any():
        raise ValueError("Invalid symbols found.")

    if working_df.duplicated(["timestamp", "symbol"]).any():
        raise ValueError("Duplicate timestamp and symbol combinations.")

    result_frames = []

    for symbol, group in working_df.groupby("symbol", sort=False):

        group = group.sort_values("timestamp").copy()

        group[f"EMA_{fast_period}"] = group["close"].ewm(
            span=fast_period,
            adjust=False
        ).mean()

        group[f"EMA_{slow_period}"] = group["close"].ewm(
            span=slow_period,
            adjust=False
        ).mean()

        result_frames.append(group)

    if not result_frames:
        raise ValueError("No valid symbol data found.")

    return (
        pd.concat(result_frames, ignore_index=True)
        .sort_values(["timestamp", "symbol"])
        .reset_index(drop=True)
    )

def calculate_risk_adjusted_score(
    return_percent,
    max_drawdown_percent,
    total_trades,
    minimum_trades=MINIMUM_TRADES_FOR_CONFIDENCE
):
    """
    Calculate a simple risk-adjusted comparison score.
    Formula: Score = (Return % / (1 + Drawdown %)) * Trade Confidence
    Trade Confidence = min(total_trades / minimum_trades, 1)
    """

    values = [
        return_percent,
        max_drawdown_percent,
        total_trades
    ]

    if not all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        for value in values
    ):
        raise ValueError("Invalid risk-adjusted score inputs.")

    if (
        max_drawdown_percent < 0
        or total_trades < 0
        or minimum_trades <= 0
    ):
        raise ValueError("Invalid drawdown or trade count.")

    trade_confidence = min(
        total_trades / minimum_trades,
        1.0
    )

    score = (
        return_percent
        / (1 + max_drawdown_percent)
    ) * trade_confidence

    return round(score, 4)

def compare_ema_strategies(
    df,
    strategy_configs=None,
    backtest_kwargs=None
):
    """
    Compare EMA crossover strategies using the same
    market data and backtesting configuration.
    """

    if strategy_configs is None:
        strategy_configs = DEFAULT_STRATEGIES

    if not isinstance(strategy_configs, (list, tuple)) or not strategy_configs:
        raise ValueError("No valid strategies supplied.")

    if backtest_kwargs is None:
        backtest_kwargs = {}

    backtest_kwargs = dict(backtest_kwargs)

    reserved_parameters = {
        "df",
        "fast_ema_period",
        "slow_ema_period"
    }

    if reserved_parameters.intersection(backtest_kwargs):
        raise ValueError(
            "Do not override dataframe or strategy EMA parameters."
        )

    names = set()
    results = []

    for config in strategy_configs:

        if not isinstance(config, dict):
            raise ValueError("Each strategy must be a dictionary.")

        name = config.get("name")
        fast_period = config.get("fast_period")
        slow_period = config.get("slow_period")

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Every strategy needs a valid name.")

        if name in names:
            raise ValueError(f"Duplicate strategy name: {name}")

        names.add(name)

        if (
            not isinstance(fast_period, int)
            or isinstance(fast_period, bool)
            or not isinstance(slow_period, int)
            or isinstance(slow_period, bool)
            or fast_period <= 0
            or slow_period <= 0
            or fast_period >= slow_period
        ):
            raise ValueError(f"Invalid EMA configuration: {name}")

        strategy_df = prepare_strategy_data(
            df,
            fast_period,
            slow_period
        )

        report = run_portfolio_backtest(
            strategy_df,
            fast_ema_period=fast_period,
            slow_ema_period=slow_period,
            **backtest_kwargs
        )

        results.append({
            "strategy": name,
            "fast_period": fast_period,
            "slow_period": slow_period,
            "report": report
        })

    comparison = []

    for result in results:

        report = result["report"]

        net_pnl = report.get("net_pnl", 0)
        return_percent = report.get("return_percent", 0)
        total_trades = report.get("total_trades", 0)
        win_rate = report.get("win_rate", 0)
        profit_factor = report.get("profit_factor")
        max_drawdown_percent = report.get(
            "max_drawdown_percent", 0
        )
        total_costs = report.get("total_costs", 0)

        score = calculate_risk_adjusted_score(
            return_percent=return_percent,
            max_drawdown_percent=max_drawdown_percent,
            total_trades=total_trades
        )

        comparison.append({
            "strategy": result["strategy"],
            "fast_period": result["fast_period"],
            "slow_period": result["slow_period"],
            "net_pnl": net_pnl,
            "return_percent": return_percent,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown_percent": max_drawdown_percent,
            "total_costs": total_costs,
            "risk_adjusted_score": score,
            "sample_status": (
                "Sufficient sample"
                if total_trades >= MINIMUM_TRADES_FOR_CONFIDENCE
                else "Insufficient sample"
            )
        })

    comparison.sort(
        key=lambda item: (
            item["risk_adjusted_score"],
            item["net_pnl"]
        ),
        reverse=True
    )

    for rank, item in enumerate(comparison, start=1):
        item["rank"] = rank

    result_lookup = {
        result["strategy"]: result
        for result in results
    }

    ranked_results = [
        result_lookup[item["strategy"]]
        for item in comparison
    ]

    return {
        "total_strategies": len(results),
        "ranking": comparison,
        "strategy_reports": ranked_results
    }

    
def build_strategy_comparison_report(comparison_result):
    """
    Build a readable summary of strategy comparison results.
    """

    if not isinstance(comparison_result, dict):
        raise ValueError("Invalid comparison result.")

    ranking = comparison_result.get("ranking")

    if not isinstance(ranking, list) or not ranking:
        raise ValueError("No strategy ranking available.")

    required_fields = {
        "strategy",
        "net_pnl",
        "return_percent",
        "max_drawdown_percent",
        "risk_adjusted_score",
        "total_trades"
    }

    for item in ranking:

        if not isinstance(item, dict):
            raise ValueError("Invalid strategy ranking entry.")

        if not required_fields.issubset(item.keys()):
            raise ValueError("Missing strategy comparison metrics.")

    best_risk_adjusted = ranking[0]

    highest_profit = max(
        ranking,
        key=lambda item: item["net_pnl"]
    )

    lowest_drawdown = min(
        ranking,
        key=lambda item: item["max_drawdown_percent"]
    )

    insufficient_sample = [
        item["strategy"]
        for item in ranking
        if item.get("sample_status") == "Insufficient sample"
    ]

    return {
        "total_strategies": len(ranking),
        "best_risk_adjusted": best_risk_adjusted,
        "highest_net_profit": highest_profit,
        "lowest_drawdown": lowest_drawdown,
        "insufficient_sample_strategies": insufficient_sample,
        "ranking": ranking
    }

def export_strategy_comparison_csv(
    comparison_result,
    output_path="reports/strategy_comparison.csv"
):
    """
    Export all strategy comparison metrics to CSV.
    """

    if not isinstance(comparison_result, dict):
        raise ValueError("Invalid comparison result.")

    ranking = comparison_result.get("ranking")

    if not isinstance(ranking, list) or not ranking:
        raise ValueError("No strategy data available for export.")

    output_file = Path(output_path)

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    comparison_df = pd.DataFrame(ranking)

    comparison_df.to_csv(
        output_file,
        index=False
    )

    return str(output_file)

def print_strategy_comparison_report(comparison_result):
    """
    Display strategy comparison results in the terminal.
    """

    report = build_strategy_comparison_report(
        comparison_result
    )

    print("\n" + "=" * 65)
    print("             EMA STRATEGY COMPARISON REPORT")
    print("=" * 65)

    print(f"\nTotal strategies compared: {report['total_strategies']}")

    best = report["best_risk_adjusted"]
    profit = report["highest_net_profit"]
    drawdown = report["lowest_drawdown"]

    print("\n1. BEST RISK-ADJUSTED STRATEGY")
    print(f"Strategy: {best['strategy']}")
    print(f"Risk-adjusted score: {best['risk_adjusted_score']}")
    print(f"Return: {best['return_percent']}%")
    print(f"Drawdown: {best['max_drawdown_percent']}%")

    print("\n2. HIGHEST NET PROFIT")
    print(f"Strategy: {profit['strategy']}")
    print(f"Net P&L: Rs. {profit['net_pnl']}")

    print("\n3. LOWEST DRAWDOWN")
    print(f"Strategy: {drawdown['strategy']}")
    print(f"Drawdown: {drawdown['max_drawdown_percent']}%")

    print("\n4. COMPLETE RANKING")

    print(
        pd.DataFrame(report["ranking"]).to_string(
            index=False
        )
    )

    if report["insufficient_sample_strategies"]:

        print("\nWARNING: Insufficient trade samples:")

        for name in report["insufficient_sample_strategies"]:
            print(f"- {name}")

    print("\n" + "=" * 65)

    return report
def split_market_data(
    df,
    train_ratio=0.70
):
    """
    Split market data chronologically using unique timestamps.

    All symbols belonging to the same timestamp remain
    in the same dataset.
    """

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("No market data available.")

    if (
        not isinstance(train_ratio, (int, float))
        or isinstance(train_ratio, bool)
        or not math.isfinite(train_ratio)
        or not 0 < train_ratio < 1
    ):
        raise ValueError("Train ratio must be between 0 and 1.")

    if "timestamp" not in df.columns:
        raise ValueError("Missing timestamp column.")

    working_df = df.copy()

    working_df["timestamp"] = pd.to_datetime(
        working_df["timestamp"],
        errors="coerce"
    )

    if working_df["timestamp"].isna().any():
        raise ValueError("Invalid timestamps found.")

    unique_timestamps = sorted(
        working_df["timestamp"].unique()
    )

    if len(unique_timestamps) < 2:
        raise ValueError(
            "At least two unique timestamps are required."
        )

    split_index = int(
        len(unique_timestamps) * train_ratio
    )

    split_index = max(
        1,
        min(split_index, len(unique_timestamps) - 1)
    )

    training_timestamps = unique_timestamps[:split_index]
    testing_timestamps = unique_timestamps[split_index:]

    train_df = working_df[
        working_df["timestamp"].isin(training_timestamps)
    ].copy()

    test_df = working_df[
        working_df["timestamp"].isin(testing_timestamps)
    ].copy()

    train_df = train_df.sort_values(
        ["timestamp", "symbol"]
    ).reset_index(drop=True)

    test_df = test_df.sort_values(
        ["timestamp", "symbol"]
    ).reset_index(drop=True)

    return {
        "train": train_df,
        "test": test_df,
        "split_timestamp": pd.Timestamp(testing_timestamps[0]),
        "training_candles": len(train_df),
        "testing_candles": len(test_df),
        "training_timestamps": len(training_timestamps),
        "testing_timestamps": len(testing_timestamps)
    }


def run_out_of_sample_validation(
    df,
    strategy_configs=None,
    train_ratio=0.70,
    backtest_kwargs=None
):
    """
    Select a strategy using training data and evaluate
    the selected strategy on unseen testing data.

    Strategy selection is performed only on training data.
    """

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("No market data available.")

    if backtest_kwargs is None:
        backtest_kwargs = {}

    if not isinstance(backtest_kwargs, dict):
        raise ValueError("Backtest settings must be a dictionary.")

    backtest_kwargs = dict(backtest_kwargs)

    reserved_parameters = {
        "df",
        "fast_ema_period",
        "slow_ema_period"
    }

    if reserved_parameters.intersection(backtest_kwargs):
        raise ValueError(
            "Do not override dataframe or strategy EMA parameters."
        )

    # 1. Split data chronologically.
    split_result = split_market_data(
        df,
        train_ratio=train_ratio
    )

    train_df = split_result["train"]
    test_df = split_result["test"]

    # 2. Compare strategies using training data only.
    training_result = compare_ema_strategies(
        train_df,
        strategy_configs=strategy_configs,
        backtest_kwargs=backtest_kwargs
    )

    if not training_result["ranking"]:
        raise ValueError("No strategy selected from training data.")

    # 3. Select the best risk-adjusted training strategy.
    selected_strategy = training_result["ranking"][0]

    fast_period = selected_strategy["fast_period"]
    slow_period = selected_strategy["slow_period"]

    # 4. Calculate EMA values using chronological full history.
    # EMA is causal: each value uses only current and earlier candles.
    # This preserves training-period warm-up for test indicators.
    prepared_test_data = prepare_strategy_data(
        df,
        fast_period=fast_period,
        slow_period=slow_period
    )

    test_timestamps = set(test_df["timestamp"])

    prepared_test_data = prepared_test_data[
        prepared_test_data["timestamp"].isin(test_timestamps)
    ].copy()

    prepared_test_data = prepared_test_data.sort_values(
        ["timestamp", "symbol"]
    ).reset_index(drop=True)

    if prepared_test_data.empty:
        raise ValueError("No testing data available.")

    # 5. Evaluate the selected strategy on unseen data.
    testing_report = run_portfolio_backtest(
        prepared_test_data,
        fast_ema_period=fast_period,
        slow_ema_period=slow_period,
        **backtest_kwargs
    )

    testing_trade_count = testing_report["total_trades"]

    return {
        "selected_strategy": selected_strategy,
        "training_report": selected_strategy,
        "testing_report": testing_report,
        "training_ranking": training_result["ranking"],
        "split_timestamp": split_result["split_timestamp"],
        "train_ratio": train_ratio,
        "test_ratio": round(1 - train_ratio, 4),
        "training_candles": split_result["training_candles"],
        "testing_candles": split_result["testing_candles"],
        "training_timestamps": split_result["training_timestamps"],
        "testing_timestamps": split_result["testing_timestamps"],
        "testing_sample_status": (
            "Sufficient sample"
            if testing_trade_count >= MINIMUM_TRADES_FOR_CONFIDENCE
            else "Insufficient sample"
        )
    }


def split_walk_forward_windows(
    df,
    train_ratio=0.60,
    test_ratio=0.10
):
    """
    Create expanding training windows and separate,
    chronological testing windows.

    Example:
    Fold 1: Train 60%, Test next 10%
    Fold 2: Train 70%, Test next 10%
    Fold 3: Train 80%, Test next 10%
    Fold 4: Train 90%, Test final 10%
    """

    if (
        df is None
        or not isinstance(df, pd.DataFrame)
        or df.empty
    ):
        raise ValueError("No market data available.")

    for ratio in (train_ratio, test_ratio):
        if (
            not isinstance(ratio, (int, float))
            or isinstance(ratio, bool)
            or not math.isfinite(ratio)
            or not 0 < ratio < 1
        ):
            raise ValueError("Ratios must be between 0 and 1.")

    if train_ratio + test_ratio > 1:
        raise ValueError(
            "Training and testing ratios cannot exceed 100%."
        )

    if "timestamp" not in df.columns:
        raise ValueError("Missing timestamp column.")

    working_df = df.copy()

    working_df["timestamp"] = pd.to_datetime(
        working_df["timestamp"],
        errors="coerce"
    )

    if working_df["timestamp"].isna().any():
        raise ValueError("Invalid timestamps found.")

    timestamps = sorted(
        working_df["timestamp"].unique()
    )

    total_timestamps = len(timestamps)

    if total_timestamps < 3:
        raise ValueError(
            "At least three unique timestamps are required."
        )

    initial_train_size = int(
        total_timestamps * train_ratio
    )

    test_window_size = int(
        total_timestamps * test_ratio
    )

    if initial_train_size < 1 or test_window_size < 1:
        raise ValueError(
            "Not enough timestamps for the requested windows."
        )

    if initial_train_size >= total_timestamps:
        raise ValueError("Training window leaves no testing data.")

    windows = []
    test_start = initial_train_size
    fold_number = 1

    while test_start < total_timestamps:

        test_end = min(
            test_start + test_window_size,
            total_timestamps
        )

        train_timestamps = timestamps[:test_start]
        test_timestamps = timestamps[test_start:test_end]

        train_df = working_df[
            working_df["timestamp"].isin(train_timestamps)
        ].copy()

        test_df = working_df[
            working_df["timestamp"].isin(test_timestamps)
        ].copy()

        sort_columns = ["timestamp"]

        if "symbol" in working_df.columns:
            sort_columns.append("symbol")

        train_df = train_df.sort_values(
            sort_columns
        ).reset_index(drop=True)

        test_df = test_df.sort_values(
            sort_columns
        ).reset_index(drop=True)

        windows.append({
            "fold": fold_number,
            "train": train_df,
            "test": test_df,
            "training_timestamps": len(train_timestamps),
            "testing_timestamps": len(test_timestamps),
            "train_start": pd.Timestamp(train_timestamps[0]),
            "train_end": pd.Timestamp(train_timestamps[-1]),
            "test_start": pd.Timestamp(test_timestamps[0]),
            "test_end": pd.Timestamp(test_timestamps[-1])
        })

        fold_number += 1
        test_start = test_end

    if len(windows) < 2:
        raise ValueError(
            "Not enough data to create at least two walk-forward folds."
        )

    return windows


def run_walk_forward_validation(
    df,
    strategy_configs=None,
    train_ratio=0.60,
    test_ratio=0.10,
    backtest_kwargs=None
):
    """
    Perform expanding-window walk-forward validation.

    Each fold:
    1. Compares strategies on training data.
    2. Selects the highest-ranked strategy.
    3. Tests that strategy on the next unseen period.
    """

    if (
        df is None
        or not isinstance(df, pd.DataFrame)
        or df.empty
    ):
        raise ValueError("No market data available.")

    if backtest_kwargs is None:
        backtest_kwargs = {}

    if not isinstance(backtest_kwargs, dict):
        raise ValueError("Backtest settings must be a dictionary.")

    backtest_kwargs = dict(backtest_kwargs)

    reserved_parameters = {
        "df",
        "fast_ema_period",
        "slow_ema_period"
    }

    if reserved_parameters.intersection(backtest_kwargs):
        raise ValueError(
            "Do not override dataframe or strategy EMA parameters."
        )

    windows = split_walk_forward_windows(
        df,
        train_ratio=train_ratio,
        test_ratio=test_ratio
    )

    fold_results = []

    for window in windows:

        # 1. Select strategy using training data only.
        training_result = compare_ema_strategies(
            window["train"],
            strategy_configs=strategy_configs,
            backtest_kwargs=backtest_kwargs
        )

        if not training_result["ranking"]:
            raise ValueError(
                f"No strategy selected in fold {window['fold']}."
            )

        selected_strategy = training_result["ranking"][0]

        fast_period = selected_strategy["fast_period"]
        slow_period = selected_strategy["slow_period"]

        # 2. Calculate causal EMA values using available history.
        # EWM uses current and previous observations, not future prices.
        prepared_data = prepare_strategy_data(
            df,
            fast_period=fast_period,
            slow_period=slow_period
        )

        # 3. Keep only this fold's unseen test timestamps.
        test_timestamps = set(
            window["test"]["timestamp"]
        )

        test_data = prepared_data[
            prepared_data["timestamp"].isin(test_timestamps)
        ].copy()

        test_data = test_data.sort_values(
            ["timestamp", "symbol"]
        ).reset_index(drop=True)

        if test_data.empty:
            raise ValueError(
                f"No test data available in fold {window['fold']}."
            )

        # 4. Evaluate selected strategy on unseen data.
        testing_report = run_portfolio_backtest(
            test_data,
            fast_ema_period=fast_period,
            slow_ema_period=slow_period,
            **backtest_kwargs
        )

        fold_results.append({
            "fold": window["fold"],
            "selected_strategy": selected_strategy["strategy"],
            "fast_period": fast_period,
            "slow_period": slow_period,
            "training_ranking": training_result["ranking"],
            "testing_report": testing_report,
            "training_timestamps": window["training_timestamps"],
            "testing_timestamps": window["testing_timestamps"],
            "train_start": window["train_start"],
            "train_end": window["train_end"],
            "test_start": window["test_start"],
            "test_end": window["test_end"]
        })

    # 5. Aggregate results from unseen testing periods.
    total_net_pnl = sum(
        result["testing_report"].get("net_pnl", 0)
        for result in fold_results
    )

    total_trades = sum(
        result["testing_report"].get("total_trades", 0)
        for result in fold_results
    )

    fold_returns = [
        result["testing_report"].get("return_percent", 0)
        for result in fold_results
    ]

    fold_drawdowns = [
        result["testing_report"].get("max_drawdown_percent", 0)
        for result in fold_results
    ]

    average_fold_return = (
        sum(fold_returns) / len(fold_returns)
    )

    profitable_folds = sum(
        1 for pnl in (
            result["testing_report"].get("net_pnl", 0)
            for result in fold_results
        )
        if pnl > 0
    )

    return {
        "total_folds": len(fold_results),
        "fold_results": fold_results,
        "total_testing_net_pnl": round(total_net_pnl, 2),
        "total_testing_trades": total_trades,
        "average_fold_return_percent": round(
            average_fold_return, 4
        ),
        "profitable_folds": profitable_folds,
        "losing_or_breakeven_folds": (
            len(fold_results) - profitable_folds
        ),
        "profitable_fold_percentage": round(
            profitable_folds / len(fold_results) * 100, 2
        ),
        "worst_fold_drawdown_percent": max(
            fold_drawdowns,
            default=0
        ),
        "overall_sample_status": (
            "Sufficient sample"
            if total_trades >= MINIMUM_TRADES_FOR_CONFIDENCE
            else "Insufficient sample"
        )
    }

def analyze_ema_parameter_sensitivity(
    df,
    fast_periods=None,
    slow_periods=None,
    baseline_fast=9,
    baseline_slow=21,
    backtest_kwargs=None
):
    """
    Test nearby EMA parameter combinations to measure
    how sensitive strategy performance is to parameter changes.

    Use training data for this analysis, not the final
    untouched out-of-sample test data.
    """

    if fast_periods is None:
        fast_periods = [7, 8, 9, 10, 11]

    if slow_periods is None:
        slow_periods = [19, 20, 21, 22, 23]

    def validate_periods(periods, label):
        if not isinstance(periods, (list, tuple)) or not periods:
            raise ValueError(f"{label} must be a non-empty list.")

        if any(
            not isinstance(period, int)
            or isinstance(period, bool)
            or period <= 0
            for period in periods
        ):
            raise ValueError(f"Invalid {label} values.")

        if len(set(periods)) != len(periods):
            raise ValueError(f"Duplicate {label} values.")

    validate_periods(fast_periods, "Fast EMA periods")
    validate_periods(slow_periods, "Slow EMA periods")

    if (
        not isinstance(baseline_fast, int)
        or isinstance(baseline_fast, bool)
        or not isinstance(baseline_slow, int)
        or isinstance(baseline_slow, bool)
        or baseline_fast <= 0
        or baseline_slow <= 0
        or baseline_fast >= baseline_slow
    ):
        raise ValueError("Invalid baseline EMA periods.")

    combinations = []

    for fast in fast_periods:
        for slow in slow_periods:
            if fast < slow:
                combinations.append({
                    "name": f"EMA {fast}/{slow}",
                    "fast_period": fast,
                    "slow_period": slow
                })

    if not combinations:
        raise ValueError("No valid EMA combinations found.")

    baseline_exists = any(
        config["fast_period"] == baseline_fast
        and config["slow_period"] == baseline_slow
        for config in combinations
    )

    if not baseline_exists:
        raise ValueError(
            "Baseline EMA combination must be included "
            "in the supplied periods."
        )

    comparison_result = compare_ema_strategies(
        df,
        strategy_configs=combinations,
        backtest_kwargs=backtest_kwargs
    )

    ranking = comparison_result["ranking"]

    baseline = next(
        item for item in ranking
        if (
            item["fast_period"] == baseline_fast
            and item["slow_period"] == baseline_slow
        )
    )

    profitable_count = sum(
        1 for item in ranking
        if item["net_pnl"] > 0
    )

    total_combinations = len(ranking)

    profitable_percentage = (
        profitable_count / total_combinations
    ) * 100

    average_return = sum(
        item["return_percent"] for item in ranking
    ) / total_combinations

    average_score = sum(
        item["risk_adjusted_score"] for item in ranking
    ) / total_combinations

    best = ranking[0]

    # This is a simple stability indicator, not a
    # statistical guarantee of future profitability.
    if profitable_percentage >= 70:
        robustness_status = "Relatively stable"
    elif profitable_percentage >= 40:
        robustness_status = "Moderately sensitive"
    else:
        robustness_status = "Highly sensitive"

    return {
        "baseline_strategy": baseline,
        "best_strategy": best,
        "total_combinations": total_combinations,
        "profitable_combinations": profitable_count,
        "profitable_percentage": round(
            profitable_percentage, 2
        ),
        "average_return_percent": round(
            average_return, 4
        ),
        "average_risk_adjusted_score": round(
            average_score, 4
        ),
        "robustness_status": robustness_status,
        "ranking": ranking
    }
