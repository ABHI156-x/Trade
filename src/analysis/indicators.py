
import pandas as pd


def _validate_period(period):
    if not isinstance(period, int) or period <= 0:
        raise ValueError("Period must be a positive integer")


def calculate_sma(df, period=20):
    _validate_period(period)

    df = df.copy()

    df[f"SMA_{period}"] = (
        df["close"].rolling(window=period).mean()
    )

    return df


def calculate_ema(df, period=9):
    _validate_period(period)

    df = df.copy()

    df[f"EMA_{period}"] = (
        df["close"].ewm(
            span=period,
            adjust=False
        ).mean()
    )

    return df


def calculate_rsi(df, period=14):
    _validate_period(period)

    df = df.copy()

    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain > 0),
        100
    )

    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain == 0),
        50
    )

    df[f"RSI_{period}"] = rsi

    return df


def calculate_macd(
    df,
    fast_period=12,
    slow_period=26,
    signal_period=9
):
    for period in (fast_period, slow_period, signal_period):
        _validate_period(period)

    if fast_period >= slow_period:
        raise ValueError(
            "MACD fast period must be smaller than slow period"
        )

    df = df.copy()

    ema_fast = df["close"].ewm(
        span=fast_period,
        adjust=False
    ).mean()

    ema_slow = df["close"].ewm(
        span=slow_period,
        adjust=False
    ).mean()

    df["MACD"] = ema_fast - ema_slow

    df["MACD_SIGNAL"] = df["MACD"].ewm(
        span=signal_period,
        adjust=False
    ).mean()

    df["MACD_HISTOGRAM"] = (
        df["MACD"] - df["MACD_SIGNAL"]
    )

    return df


def calculate_volume_average(df, period=20):
    _validate_period(period)

    df = df.copy()

    df[f"VOLUME_SMA_{period}"] = (
        df["volume"].rolling(window=period).mean()
    )

    return df


def calculate_all_indicators(
    df,
    ema_periods=(9, 21, 50),
    sma_period=20,
    rsi_period=14,
    volume_period=20
):
    df = df.copy()

    if len(set(ema_periods)) != len(ema_periods):
        raise ValueError("EMA periods must be unique")

    for period in ema_periods:
        df = calculate_ema(df, period)

    df = calculate_sma(df, sma_period)

    df = calculate_rsi(df, rsi_period)

    df = calculate_macd(df)

    df = calculate_volume_average(df, volume_period)

    return df


def calculate_indicators_by_symbol(
    df,
    ema_periods=(9, 21, 50),
    sma_period=20,
    rsi_period=14,
    volume_period=20
):
    """
    Calculate indicators independently for each stock.

    This prevents one stock's prices from affecting
    another stock's indicators.
    """

    if "symbol" not in df.columns:
        raise ValueError("Missing symbol column")

    if "timestamp" not in df.columns:
        raise ValueError("Missing timestamp column")

    frames = []

    for symbol, group in df.groupby("symbol", sort=False):

        group = group.sort_values("timestamp").copy()

        calculated = calculate_all_indicators(
            group,
            ema_periods=ema_periods,
            sma_period=sma_period,
            rsi_period=rsi_period,
            volume_period=volume_period
        )

        frames.append(calculated)

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)

    return result.sort_values(
        by=["timestamp", "symbol"]
    ).reset_index(drop=True)
