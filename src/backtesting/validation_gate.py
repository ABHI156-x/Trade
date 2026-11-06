
import math


def _valid_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def validate_strategy_evidence(
    strategy_name,
    out_of_sample_result,
    walk_forward_result,
    minimum_trades=10,
    max_drawdown_percent=5.0,
    minimum_walk_forward_folds=2,
    minimum_profitable_fold_ratio=0.50
):
    """
    Validate one strategy using out-of-sample and walk-forward results.

    Only walk-forward folds in which this strategy was selected
    are used to evaluate its performance.
    """

    if not isinstance(strategy_name, str) or not strategy_name.strip():
        raise ValueError("Invalid strategy name.")

    if (
        not isinstance(minimum_trades, int)
        or isinstance(minimum_trades, bool)
        or minimum_trades <= 0
    ):
        raise ValueError("Minimum trades must be positive.")

    if (
        not isinstance(minimum_walk_forward_folds, int)
        or isinstance(minimum_walk_forward_folds, bool)
        or minimum_walk_forward_folds <= 0
    ):
        raise ValueError("Minimum walk-forward folds must be positive.")

    if (
        not _valid_number(max_drawdown_percent)
        or max_drawdown_percent < 0
    ):
        raise ValueError("Invalid maximum drawdown.")

    if (
        not _valid_number(minimum_profitable_fold_ratio)
        or not 0 < minimum_profitable_fold_ratio <= 1
    ):
        raise ValueError("Invalid profitable fold ratio.")

    if not isinstance(out_of_sample_result, dict):
        raise ValueError("Invalid out-of-sample result.")

    if not isinstance(walk_forward_result, dict):
        raise ValueError("Invalid walk-forward result.")

    reasons = []

    # --------------------------------------------------
    # 1. Out-of-sample validation
    # --------------------------------------------------

    selected = out_of_sample_result.get("selected_strategy")

    if not isinstance(selected, dict):
        raise ValueError("Missing out-of-sample selected strategy.")

    if selected.get("strategy") != strategy_name:
        reasons.append(
            "Strategy does not match the out-of-sample selected strategy."
        )

    testing_report = out_of_sample_result.get("testing_report")

    if not isinstance(testing_report, dict):
        raise ValueError("Missing out-of-sample testing report.")

    oos_trades = testing_report.get("total_trades")
    oos_pnl = testing_report.get("net_pnl")
    oos_return = testing_report.get("return_percent")
    oos_drawdown = testing_report.get("max_drawdown_percent")

    if (
        not isinstance(oos_trades, int)
        or isinstance(oos_trades, bool)
        or oos_trades < 0
    ):
        raise ValueError("Invalid out-of-sample trade count.")

    for value in (oos_pnl, oos_return, oos_drawdown):
        if not _valid_number(value):
            raise ValueError("Invalid out-of-sample performance metric.")

    if oos_drawdown < 0:
        raise ValueError("Out-of-sample drawdown cannot be negative.")

    if oos_trades < minimum_trades:
        reasons.append("Insufficient out-of-sample trades.")

    if oos_pnl <= 0:
        reasons.append("Out-of-sample net P&L is not positive.")

    if oos_return <= 0:
        reasons.append("Out-of-sample return is not positive.")

    if oos_drawdown > max_drawdown_percent:
        reasons.append("Out-of-sample drawdown exceeds the limit.")

    # --------------------------------------------------
    # 2. Walk-forward validation
    # --------------------------------------------------

    folds = walk_forward_result.get("fold_results")

    if not isinstance(folds, list) or not folds:
        raise ValueError("Missing walk-forward fold results.")

    selected_folds = []

    for fold in folds:

        if not isinstance(fold, dict):
            raise ValueError("Invalid walk-forward fold.")

        fold_strategy = fold.get("selected_strategy")

        if not isinstance(fold_strategy, str):
            raise ValueError("Invalid selected strategy in walk-forward fold.")

        if fold_strategy != strategy_name:
            continue

        report = fold.get("testing_report")

        if not isinstance(report, dict):
            raise ValueError("Missing walk-forward testing report.")

        pnl = report.get("net_pnl")
        trades = report.get("total_trades")
        drawdown = report.get("max_drawdown_percent")

        if (
            not isinstance(trades, int)
            or isinstance(trades, bool)
            or trades < 0
        ):
            raise ValueError("Invalid walk-forward trade count.")

        if not all(_valid_number(value) for value in (pnl, drawdown)):
            raise ValueError("Invalid walk-forward performance metrics.")

        if drawdown < 0:
            raise ValueError("Walk-forward drawdown cannot be negative.")

        selected_folds.append({
            "fold": fold.get("fold"),
            "net_pnl": pnl,
            "total_trades": trades,
            "max_drawdown_percent": drawdown
        })

    selected_fold_count = len(selected_folds)

    if selected_fold_count < minimum_walk_forward_folds:
        reasons.append(
            "Strategy was selected in too few walk-forward folds."
        )

    wf_total_trades = sum(
        fold["total_trades"]
        for fold in selected_folds
    )

    wf_total_pnl = sum(
        fold["net_pnl"]
        for fold in selected_folds
    )

    profitable_folds = sum(
        1 for fold in selected_folds
        if fold["net_pnl"] > 0
    )

    profitable_fold_ratio = (
        profitable_folds / selected_fold_count
        if selected_fold_count else 0
    )

    worst_fold_drawdown = max(
        (
            fold["max_drawdown_percent"]
            for fold in selected_folds
        ),
        default=0
    )

    if wf_total_trades < minimum_trades:
        reasons.append(
            "Insufficient walk-forward trades for this strategy."
        )

    if wf_total_pnl <= 0:
        reasons.append(
            "Walk-forward net P&L is not positive."
        )

    if (
        selected_fold_count >= minimum_walk_forward_folds
        and profitable_fold_ratio < minimum_profitable_fold_ratio
    ):
        reasons.append(
            "Too few walk-forward folds were profitable."
        )

    if worst_fold_drawdown > max_drawdown_percent:
        reasons.append(
            "A walk-forward fold exceeded the drawdown limit."
        )

    passed = len(reasons) == 0

    return {
        "strategy": strategy_name,
        "status": "PASSED" if passed else "FAILED",
        "passed": passed,
        "out_of_sample": {
            "total_trades": oos_trades,
            "net_pnl": round(float(oos_pnl), 2),
            "return_percent": round(float(oos_return), 4),
            "max_drawdown_percent": round(float(oos_drawdown), 4)
        },
        "walk_forward": {
            "total_folds": len(folds),
            "selected_folds": selected_fold_count,
            "total_trades": wf_total_trades,
            "net_pnl": round(wf_total_pnl, 2),
            "profitable_folds": profitable_folds,
            "profitable_fold_ratio": round(
                profitable_fold_ratio, 4
            ),
            "worst_fold_drawdown_percent": round(
                worst_fold_drawdown, 4
            )
        },
        "reasons": reasons
    }
