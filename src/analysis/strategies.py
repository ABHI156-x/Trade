
import pandas as pd


def generate_ema_crossover_signals(
    df,
    fast_period=9,
    slow_period=21
):
    """
    Generate EMA crossover signals.

    BUY:
        Fast EMA crosses above slow EMA.

    SELL:
        Fast EMA crosses below slow EMA.

    NEUTRAL:
        No crossover.

    This function generates signals only.
    It does not execute trades.
    """

    if fast_period <= 0 or slow_period <= 0:
        raise ValueError("EMA periods must be positive")

    if fast_period >= slow_period:
        raise ValueError(
            "Fast EMA period must be smaller than slow EMA period"
        )

    fast_column = f"EMA_{fast_period}"
    slow_column = f"EMA_{slow_period}"

    if fast_column not in df.columns:
        raise ValueError(f"Missing indicator: {fast_column}")

    if slow_column not in df.columns:
        raise ValueError(f"Missing indicator: {slow_column}")

    result = df.copy()

    previous_fast = result[fast_column].shift(1)
    previous_slow = result[slow_column].shift(1)

    bullish_crossover = (
        (previous_fast <= previous_slow)
        & (result[fast_column] > result[slow_column])
    )

    bearish_crossover = (
        (previous_fast >= previous_slow)
        & (result[fast_column] < result[slow_column])
    )

    result["strategy_signal"] = "NEUTRAL"

    result.loc[bullish_crossover, "strategy_signal"] = "BUY"

    result.loc[bearish_crossover, "strategy_signal"] = "SELL"

    return result


def get_ema_strategy_configs():
    """
    Return predefined EMA crossover strategies.
    """

    return [
        {
            "name": "EMA 5/20",
            "fast_period": 5,
            "slow_period": 20
        },
        {
            "name": "EMA 9/21",
            "fast_period": 9,
            "slow_period": 21
        },
        {
            "name": "EMA 12/26",
            "fast_period": 12,
            "slow_period": 26
        },
        {
            "name": "EMA 20/50",
            "fast_period": 20,
            "slow_period": 50
        }
    ]
