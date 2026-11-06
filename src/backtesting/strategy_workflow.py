
import pandas as pd

from src.backtesting.regime_strategy_comparison import (
    compare_strategies_by_market_regime
)
from src.backtesting.strategy_comparison import (
    run_out_of_sample_validation,
    run_walk_forward_validation
)
from src.backtesting.strategy_comparison import (
    run_out_of_sample_validation,
    run_walk_forward_validation
)

from src.backtesting.validation_gate import (
    validate_strategy_evidence
)

from src.backtesting.strategy_selector import (
    select_strategy_for_regime
)


def _failed_validation(strategy_name, reason):
    return {
        "strategy": strategy_name,
        "status": "FAILED",
        "passed": False,
        "reasons": [reason]
    }


def _generate_strategy_validation(
    df,
    strategy_config,
    backtest_kwargs=None,
    oos_kwargs=None,
    walk_forward_kwargs=None
):
    """
    Generate independent OOS and walk-forward evidence
    for one strategy.
    """

    strategy_configs = [strategy_config]

    oos_result = run_out_of_sample_validation(
        df,
        strategy_configs=strategy_configs,
        backtest_kwargs=backtest_kwargs,
        **(oos_kwargs or {})
    )

    walk_forward_result = run_walk_forward_validation(
        df,
        strategy_configs=strategy_configs,
        backtest_kwargs=backtest_kwargs,
        **(walk_forward_kwargs or {})
    )

    return {
        "out_of_sample_result": oos_result,
        "walk_forward_result": walk_forward_result
    }


def run_regime_strategy_workflow(
    df,
    current_regime,
    out_of_sample_result=None,
    walk_forward_result=None,
    strategy_configs=None,
    backtest_kwargs=None,
    regime_kwargs=None,
    minimum_trades=10,
    max_drawdown_percent=5.0,
    validation_kwargs=None,
    validation_data_by_strategy=None,
    oos_kwargs=None,
    walk_forward_kwargs=None
):
    """
    Complete regime-aware strategy selection workflow.

    Validation modes:

    1. Automatic:
       Generate OOS and walk-forward evidence independently.

    2. Independent:
       Use validation_data_by_strategy.

    3. Legacy:
       Use shared OOS and walk-forward evidence.

    Research and paper-trading only. No live orders.
    """

    # --------------------------------------------------
    # 1. Validate basic inputs
    # --------------------------------------------------

    if (
        df is None
        or not isinstance(df, pd.DataFrame)
        or df.empty
    ):
        raise ValueError("Market data cannot be empty.")

    if (
        not isinstance(current_regime, str)
        or not current_regime.strip()
    ):
        raise ValueError("A valid current market regime is required.")

    current_regime = current_regime.strip()

    if (
        not isinstance(minimum_trades, int)
        or isinstance(minimum_trades, bool)
        or minimum_trades <= 0
    ):
        raise ValueError("Minimum trades must be a positive integer.")

    if (
        not isinstance(max_drawdown_percent, (int, float))
        or isinstance(max_drawdown_percent, bool)
        or max_drawdown_percent < 0
    ):
        raise ValueError("Maximum drawdown must be non-negative.")

    # --------------------------------------------------
    # 2. Identify validation mode
    # --------------------------------------------------

    if validation_data_by_strategy is not None:

        if not isinstance(validation_data_by_strategy, dict):
            raise ValueError(
                "Strategy validation data must be a dictionary."
            )

        validation_mode = "independent"

    elif (
        out_of_sample_result is not None
        or walk_forward_result is not None
    ):

        if not isinstance(out_of_sample_result, dict):
            raise ValueError("Invalid out-of-sample result.")

        if not isinstance(walk_forward_result, dict):
            raise ValueError("Invalid walk-forward result.")

        validation_mode = "shared"

    else:
        validation_mode = "automatic"

    # --------------------------------------------------
    # 3. Validate optional settings
    # --------------------------------------------------

    if validation_kwargs is None:
        validation_kwargs = {}

    if oos_kwargs is None:
        oos_kwargs = {}

    if walk_forward_kwargs is None:
        walk_forward_kwargs = {}

    if not isinstance(validation_kwargs, dict):
        raise ValueError("Validation settings must be a dictionary.")

    if not isinstance(oos_kwargs, dict):
        raise ValueError("OOS settings must be a dictionary.")

    if not isinstance(walk_forward_kwargs, dict):
        raise ValueError("Walk-forward settings must be a dictionary.")

    validation_kwargs = dict(validation_kwargs)
    oos_kwargs = dict(oos_kwargs)
    walk_forward_kwargs = dict(walk_forward_kwargs)

    reserved_validation_parameters = {
        "strategy_name",
        "out_of_sample_result",
        "walk_forward_result",
        "minimum_trades",
        "max_drawdown_percent"
    }

    if reserved_validation_parameters.intersection(validation_kwargs):
        raise ValueError(
            "Do not override required validation parameters."
        )

    reserved_backtest_parameters = {
        "df",
        "fast_ema_period",
        "slow_ema_period"
    }

    for settings in (backtest_kwargs or {},):

        if not isinstance(settings, dict):
            raise ValueError("Backtest settings must be a dictionary.")

        if reserved_backtest_parameters.intersection(settings):
            raise ValueError(
                "Do not override dataframe or EMA parameters."
            )

    # Prevent duplicate keyword arguments.
    if {"strategy_configs", "backtest_kwargs"}.intersection(oos_kwargs):
        raise ValueError("OOS settings cannot override strategy inputs.")

    if {"strategy_configs", "backtest_kwargs"}.intersection(
        walk_forward_kwargs
    ):
        raise ValueError(
            "Walk-forward settings cannot override strategy inputs."
        )

    # --------------------------------------------------
    # 4. Compare strategies by market regime
    # --------------------------------------------------

    comparison_result = compare_strategies_by_market_regime(
        df,
        strategy_configs=strategy_configs,
        backtest_kwargs=backtest_kwargs,
        regime_kwargs=regime_kwargs
    )

    if not isinstance(comparison_result, dict):
        raise ValueError("Invalid regime comparison result.")

    regime_rankings = comparison_result.get("regime_rankings")

    if not isinstance(regime_rankings, dict):
        raise ValueError("Missing regime rankings.")

    candidates = regime_rankings.get(current_regime, [])

    if not isinstance(candidates, list):
        raise ValueError("Invalid regime candidate list.")

    # --------------------------------------------------
    # 5. Build strategy configuration lookup
    # --------------------------------------------------

    strategy_config_lookup = {}

    if validation_mode == "automatic":

        strategy_details = comparison_result.get(
            "strategy_details"
        )

        if not isinstance(strategy_details, list):
            raise ValueError(
                "Automatic validation requires strategy details."
            )

        for detail in strategy_details:

            if not isinstance(detail, dict):
                raise ValueError("Invalid strategy detail.")

            name = detail.get("strategy")
            fast_period = detail.get("fast_period")
            slow_period = detail.get("slow_period")

            if (
                not isinstance(name, str)
                or not name.strip()
                or not isinstance(fast_period, int)
                or isinstance(fast_period, bool)
                or not isinstance(slow_period, int)
                or isinstance(slow_period, bool)
                or fast_period <= 0
                or slow_period <= 0
                or fast_period >= slow_period
            ):
                raise ValueError(
                    "Invalid strategy EMA configuration."
                )

            if name in strategy_config_lookup:
                raise ValueError(
                    "Duplicate strategy details found."
                )

            strategy_config_lookup[name] = {
                "name": name,
                "fast_period": fast_period,
                "slow_period": slow_period
            }

    # --------------------------------------------------
    # 6. Validate every current-regime candidate
    # --------------------------------------------------

    validation_results = {}

    for candidate in candidates:

        if not isinstance(candidate, dict):
            raise ValueError("Invalid strategy candidate.")

        strategy_name = candidate.get("strategy")

        if (
            not isinstance(strategy_name, str)
            or not strategy_name.strip()
        ):
            raise ValueError("Invalid strategy candidate name.")

        strategy_name = strategy_name.strip()

        if strategy_name in validation_results:
            raise ValueError("Duplicate strategy names.")

        try:

            # ------------------------------------------
            # Mode A: Automatic evidence generation
            # ------------------------------------------

            if validation_mode == "automatic":

                strategy_config = strategy_config_lookup.get(
                    strategy_name
                )

                if strategy_config is None:
                    validation_results[strategy_name] = (
                        _failed_validation(
                            strategy_name,
                            "Strategy EMA configuration is missing."
                        )
                    )
                    continue

                evidence = _generate_strategy_validation(
                    df=df,
                    strategy_config=strategy_config,
                    backtest_kwargs=backtest_kwargs,
                    oos_kwargs=oos_kwargs,
                    walk_forward_kwargs=walk_forward_kwargs
                )

                candidate_oos = evidence["out_of_sample_result"]
                candidate_wf = evidence["walk_forward_result"]

            # ------------------------------------------
            # Mode B: Independent supplied evidence
            # ------------------------------------------

            elif validation_mode == "independent":

                evidence = validation_data_by_strategy.get(
                    strategy_name
                )

                if not isinstance(evidence, dict):
                    validation_results[strategy_name] = (
                        _failed_validation(
                            strategy_name,
                            "Independent validation evidence is missing."
                        )
                    )
                    continue

                candidate_oos = evidence.get(
                    "out_of_sample_result"
                )

                candidate_wf = evidence.get(
                    "walk_forward_result"
                )

            # ------------------------------------------
            # Mode C: Legacy shared evidence
            # ------------------------------------------

            else:
                candidate_oos = out_of_sample_result
                candidate_wf = walk_forward_result

            if (
                not isinstance(candidate_oos, dict)
                or not isinstance(candidate_wf, dict)
            ):
                validation_results[strategy_name] = (
                    _failed_validation(
                        strategy_name,
                        "Candidate validation evidence is incomplete."
                    )
                )
                continue

            # ------------------------------------------
            # Run the validation gate
            # ------------------------------------------

            validation_results[strategy_name] = (
                validate_strategy_evidence(
                    strategy_name=strategy_name,
                    out_of_sample_result=candidate_oos,
                    walk_forward_result=candidate_wf,
                    minimum_trades=minimum_trades,
                    max_drawdown_percent=max_drawdown_percent,
                    **validation_kwargs
                )
            )

        except (ValueError, TypeError, KeyError) as error:

            validation_results[strategy_name] = (
                _failed_validation(
                    strategy_name,
                    f"Validation failed: {error}"
                )
            )

    # --------------------------------------------------
    # 7. Select only a validated strategy
    # --------------------------------------------------

    selection_result = select_strategy_for_regime(
        comparison_result=comparison_result,
        current_regime=current_regime,
        minimum_trades=minimum_trades,
        max_drawdown_percent=max_drawdown_percent,
        validation_results=validation_results
    )

    # --------------------------------------------------
    # 8. Return complete workflow report
    # --------------------------------------------------

    return {
        "status": selection_result["status"],
        "validation_mode": validation_mode,
        "current_regime": current_regime,
        "selected_strategy": selection_result["selected_strategy"],
        "top_candidate": selection_result["top_candidate"],
        "selection_result": selection_result,
        "validation_results": validation_results,
        "regime_comparison": comparison_result,
        "total_candidates": len(candidates),
        "validated_candidates": sum(
            1
            for result in validation_results.values()
            if result.get("passed") is True
        ),
        "note": (
            "Research-only strategy selection. "
            "Historical and validation results do not guarantee "
            "future performance. No live orders are permitted."
        )
    }
