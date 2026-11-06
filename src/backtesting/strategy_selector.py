import math

DEFAULT_MINIMUM_TRADES = 10
DEFAULT_MAX_DRAWDOWN_PERCENT = 5.0

def _valid_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )

def select_strategy_for_regime(
    comparison_result,
    current_regime,
    minimum_trades=DEFAULT_MINIMUM_TRADES,
    max_drawdown_percent=DEFAULT_MAX_DRAWDOWN_PERCENT,
    validation_results=None):
    """
    Select a historically suitable strategy for a market regime.

    This is a paper-trading research filter, not a live trading signal.

    Without confirmed out-of-sample or walk-forward validation,
    the result remains NO_TRADE.
    """

    if not isinstance(comparison_result, dict):
        raise ValueError("Comparison result must be a dictionary.")

    if not isinstance(current_regime, str) or not current_regime.strip():
        raise ValueError("A valid market regime is required.")

    current_regime = current_regime.strip()

    if (
        not isinstance(minimum_trades, int)
        or isinstance(minimum_trades, bool)
        or minimum_trades <= 0
    ):
        raise ValueError("Minimum trades must be a positive integer.")

    if (
        not _valid_number(max_drawdown_percent)
        or max_drawdown_percent < 0
    ):
        raise ValueError("Maximum drawdown must be finite and non-negative.")

    if validation_results is not None and not isinstance(validation_results, dict):
        raise ValueError("validation_results must be a dict or None.")

    regime_rankings = comparison_result.get("regime_rankings")

    if not isinstance(regime_rankings, dict):
        raise ValueError("Missing or invalid regime rankings.")

    if current_regime not in regime_rankings:
        return {
            "status": "NO_TRADE",
            "current_regime": current_regime,
            "selected_strategy": None,
            "top_candidate": None,
            "evaluated_candidates": [],
            "reasons": ["No historical strategy results exist for this regime."]
        }

    candidates = regime_rankings[current_regime]

    if not isinstance(candidates, list):
        raise ValueError("Regime ranking must be a list.")

    if not candidates:
        return {
            "status": "NO_TRADE",
            "current_regime": current_regime,
            "selected_strategy": None,
            "top_candidate": None,
            "evaluated_candidates": [],
            "reasons": ["No strategies were evaluated for this regime."]
        }

    evaluated = []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("Invalid strategy candidate.")

        required_fields = {
            "strategy",
            "total_trades",
            "net_pnl",
            "max_drawdown_percent",
            "risk_adjusted_score"
        }

        if not required_fields.issubset(candidate):
            raise ValueError("Missing candidate performance fields.")

        strategy_name = candidate["strategy"]
        if not isinstance(strategy_name, str) or not strategy_name.strip():
            raise ValueError("Invalid strategy name.")

        total_trades = candidate["total_trades"]
        net_pnl = candidate["net_pnl"]
        drawdown = candidate["max_drawdown_percent"]
        score = candidate["risk_adjusted_score"]

        if not isinstance(total_trades, int) or isinstance(total_trades, bool) or total_trades < 0:
            raise ValueError("Invalid trade count.")
        if not _valid_number(net_pnl):
            raise ValueError("Invalid net P&L.")
        if not _valid_number(drawdown) or drawdown < 0:
            raise ValueError("Invalid drawdown.")
        if not _valid_number(score):
            raise ValueError("Invalid risk-adjusted score.")

        reasons = []
        if total_trades < minimum_trades:
            reasons.append("Insufficient completed trades.")
        if net_pnl <= 0:
            reasons.append("Historical net P&L is not positive.")
        if drawdown > max_drawdown_percent:
            reasons.append("Drawdown exceeds the configured limit.")
        if score <= 0:
            reasons.append("Risk-adjusted score is not positive.")

        evaluated.append({
            "strategy": strategy_name,
            "total_trades": total_trades,
            "net_pnl": round(float(net_pnl), 2),
            "max_drawdown_percent": round(float(drawdown), 4),
            "risk_adjusted_score": round(float(score), 6),
            "eligible": len(reasons) == 0,
            "rejection_reasons": reasons
        })

    eligible = [item for item in evaluated if item["eligible"]]
    eligible.sort(
        key=lambda item: (item["risk_adjusted_score"], item["net_pnl"], -item["max_drawdown_percent"]),
        reverse=True
    )

    top_candidate = eligible[0] if eligible else None

    if not eligible:
        return {
            "status": "NO_TRADE",
            "current_regime": current_regime,
            "selected_strategy": None,
            "top_candidate": None,
            "evaluated_candidates": evaluated,
            "reasons": ["No strategy passed the configured performance filters."]
        }

    if not isinstance(validation_results, dict):
        validation_results = {}

    validated_eligible = []

    for candidate in eligible:
        validation = validation_results.get(candidate["strategy"])

        if not isinstance(validation, dict):
            candidate["validation_status"] = "MISSING"
            candidate["validation_reasons"] = ["No automatic validation evidence supplied."]
            continue

        if validation.get("passed") is not True:
            candidate["validation_status"] = "FAILED"
            candidate["validation_reasons"] = validation.get("reasons", ["Strategy validation failed."])
            continue

        # validate reasons structure
        v_reasons = validation.get("reasons", [])
        if not isinstance(v_reasons, list):
            candidate["validation_status"] = "FAILED"
            candidate["validation_reasons"] = ["Invalid validation evidence structure."]
            continue

        candidate["validation_status"] = "PASSED"
        candidate["validation_reasons"] = []
        validated_eligible.append(candidate)

    if not validated_eligible:
        return {
            "status": "NO_TRADE",
            "current_regime": current_regime,
            "selected_strategy": None,
            "top_candidate": top_candidate,
            "evaluated_candidates": evaluated,
            "reasons": ["No eligible strategy passed automatic validation."]
        }

    validated_eligible.sort(
        key=lambda item: (item["risk_adjusted_score"], item["net_pnl"], -item["max_drawdown_percent"]),
        reverse=True
    )

    selected = validated_eligible[0]

    return {
        "status": "SELECTED",
        "current_regime": current_regime,
        "selected_strategy": selected,
        "top_candidate": top_candidate,
        "evaluated_candidates": evaluated,
        "reasons": [
            "Historical performance filters passed.",
            "Automatic validation evidence passed."
        ]
    }