
import math
import pandas as pd


def classify_market_regime(
    df,
    fast_period=9,
    slow_period=21,
    atr_period=14,
    trend_threshold=0.10,
    volatility_threshold=1.50
):
    """
    Classify market conditions for one stock.

    Regimes:
    - TRENDING_UP
    - TRENDING_DOWN
    - SIDEWAYS
    - HIGH_VOLATILITY
    - UNKNOWN

    ATR percentage = ATR / Close * 100
    Trend strength = absolute EMA spread / Close * 100
    """

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("No market data available.")

    periods = [fast_period, slow_period, atr_period]

    for period in periods:
        if (
            not isinstance(period, int)
            or isinstance(period, bool)
            or period <= 0
        ):
            raise ValueError("Periods must be positive integers.")

    if fast_period >= slow_period:
        raise ValueError("Fast EMA must be smaller than slow EMA.")

    thresholds = [trend_threshold, volatility_threshold]

    for threshold in thresholds:
        if (
            not isinstance(threshold, (int, float))
            or isinstance(threshold, bool)
            or not math.isfinite(threshold)
            or threshold < 0
        ):
            raise ValueError("Thresholds must be finite and non-negative.")

    required_columns = {"high", "low", "close"}

    if not required_columns.issubset(df.columns):
        raise ValueError("Missing required OHLC columns.")

    result = df.copy()

    for column in ["high", "low", "close"]:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce"
        )

        if result[column].isna().any():
            raise ValueError(f"Invalid {column} values.")

        if not result[column].map(math.isfinite).all():
            raise ValueError(f"{column} values must be finite.")

        if (result[column] <= 0).any():
            raise ValueError(f"{column} values must be positive.")

    if (result["high"] < result["low"]).any():
        raise ValueError("High cannot be lower than low.")

    if (
        (result["close"] > result["high"])
        | (result["close"] < result["low"])
    ).any():
        raise ValueError("Close must be between high and low.")

    # Calculate EMAs.
    result[f"EMA_{fast_period}"] = result["close"].ewm(
        span=fast_period,
        adjust=False
    ).mean()

    result[f"EMA_{slow_period}"] = result["close"].ewm(
        span=slow_period,
        adjust=False
    ).mean()

    # Calculate True Range.
    previous_close = result["close"].shift(1)

    true_range = pd.concat(
        [
            result["high"] - result["low"],
            (result["high"] - previous_close).abs(),
            (result["low"] - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    # ATR using rolling mean.
    result["ATR"] = true_range.rolling(
        window=atr_period,
        min_periods=atr_period
    ).mean()

    # Normalize ATR by closing price.
    result["ATR_PERCENT"] = (
        result["ATR"] / result["close"]
    ) * 100

    # Measure EMA separation.
    result["TREND_STRENGTH"] = (
        (
            result[f"EMA_{fast_period}"]
            - result[f"EMA_{slow_period}"]
        ).abs()
        / result["close"]
    ) * 100

    # EMA direction.
    fast_ema_change = result[f"EMA_{fast_period}"].diff()

    regimes = []

    for index in result.index:

        atr_percent = result.at[index, "ATR_PERCENT"]
        trend_strength = result.at[index, "TREND_STRENGTH"]
        ema_change = fast_ema_change.loc[index]

        if (
            pd.isna(atr_percent)
            or pd.isna(trend_strength)
            or pd.isna(ema_change)
        ):
            regimes.append("UNKNOWN")

        elif atr_percent >= volatility_threshold:
            regimes.append("HIGH_VOLATILITY")

        elif trend_strength < trend_threshold:
            regimes.append("SIDEWAYS")

        elif (
            result.at[index, f"EMA_{fast_period}"]
            > result.at[index, f"EMA_{slow_period}"]
            and ema_change > 0
        ):
            regimes.append("TRENDING_UP")

        elif (
            result.at[index, f"EMA_{fast_period}"]
            < result.at[index, f"EMA_{slow_period}"]
            and ema_change < 0
        ):
            regimes.append("TRENDING_DOWN")

        else:
            regimes.append("SIDEWAYS")

    result["MARKET_REGIME"] = regimes

    return result


def classify_regimes_by_symbol(
    df,
    fast_period=9,
    slow_period=21,
    atr_period=14,
    trend_threshold=0.10,
    volatility_threshold=1.50
):
    """
    Calculate market regimes independently for each symbol.
    """

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("No market data available.")

    if "symbol" not in df.columns:
        raise ValueError("Missing symbol column.")

    if "timestamp" not in df.columns:
        raise ValueError("Missing timestamp column.")

    if df["symbol"].isna().any():
        raise ValueError("Invalid symbols found.")

    working_df = df.copy()

    working_df["timestamp"] = pd.to_datetime(
        working_df["timestamp"],
        errors="coerce"
    )

    if working_df["timestamp"].isna().any():
        raise ValueError("Invalid timestamps found.")

    if working_df.duplicated(["timestamp", "symbol"]).any():
        raise ValueError("Duplicate timestamp and symbol combinations.")

    frames = []

    for symbol, group in working_df.groupby("symbol", sort=False):

        group = group.sort_values("timestamp").copy()

        classified = classify_market_regime(
            group,
            fast_period=fast_period,
            slow_period=slow_period,
            atr_period=atr_period,
            trend_threshold=trend_threshold,
            volatility_threshold=volatility_threshold
        )

        frames.append(classified)

    return (
        pd.concat(frames, ignore_index=True)
        .sort_values(["timestamp", "symbol"])
        .reset_index(drop=True)
    )
