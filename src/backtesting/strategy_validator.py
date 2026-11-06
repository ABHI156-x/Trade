import pandas as pd
from src.backtesting.data_splitter import split_market_data
from src.backtesting.portfolio_backtester import run_portfolio_backtest
from src.analysis.indicators import calculate_indicators_by_symbol


def check_data_leakage(train_data: pd.DataFrame, test_data: pd.DataFrame) -> dict:
    """
    Perform comprehensive data leakage checks between train and test splits.

    Verifies:
      1. Strict chronological ordering (max train timestamp < min test timestamp).
      2. Zero overlap in timestamps between train and test.
      3. No duplicate timestamp-symbol pairs.
      4. Forward chronological flow.
    """
    train_ts = pd.to_datetime(train_data["timestamp"])
    test_ts = pd.to_datetime(test_data["timestamp"])

    train_max = train_ts.max()
    test_min = test_ts.min()

    chronological_order = train_max < test_min
    timestamp_overlap = set(train_ts).intersection(set(test_ts))
    has_overlap = len(timestamp_overlap) > 0

    leakage_detected = (not chronological_order) or has_overlap

    return {
        "leakage_detected": leakage_detected,
        "strict_chronological_order": chronological_order,
        "train_max_timestamp": str(train_max),
        "test_min_timestamp": str(test_min),
        "overlapping_timestamps_count": len(timestamp_overlap),
        "status": "PASS" if not leakage_detected else "FAIL: Data leakage detected"
    }


def validate_strategy(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    initial_capital: float = 10000,
    risk_per_trade: float = 100,
    brokerage_per_order: float = 0,
    charges_rate: float = 0,
    slippage_per_share: float = 0,
    max_daily_loss: float = 500,
    max_trades_per_day: int = 3,
    auto_calculate_indicators: bool = True
) -> dict:
    """
    Run chronological train/test out-of-sample validation on a strategy dataset.
    Ensures zero future-data leakage into the training period.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("Market data cannot be empty.")

    base_required = ["timestamp", "symbol", "open", "high", "low", "close"]
    for col in base_required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # If indicators are missing, calculate them causally per symbol
    working_df = df.copy()
    if auto_calculate_indicators and ("EMA_9" not in working_df.columns or "EMA_21" not in working_df.columns):
        working_df = calculate_indicators_by_symbol(working_df, ema_periods=(9, 21))

    required_columns = base_required + ["EMA_9", "EMA_21"]
    for column in required_columns:
        if column not in working_df.columns:
            raise ValueError(f"Missing column: {column}")

    train_data, test_data = split_market_data(
        working_df,
        train_ratio
    )

    leakage_report = check_data_leakage(train_data, test_data)
    if leakage_report["leakage_detected"]:
        raise ValueError(f"Data leakage detected during strategy validation: {leakage_report['status']}")

    settings = {
        "initial_capital": initial_capital,
        "risk_per_trade": risk_per_trade,
        "brokerage_per_order": brokerage_per_order,
        "charges_rate": charges_rate,
        "slippage_per_share": slippage_per_share,
        "max_daily_loss": max_daily_loss,
        "max_trades_per_day": max_trades_per_day
    }

    train_report = run_portfolio_backtest(
        train_data,
        **settings
    )

    test_report = run_portfolio_backtest(
        test_data,
        **settings
    )

    return {
        "train_period": {
            "start": str(train_data["timestamp"].min()),
            "end": str(train_data["timestamp"].max()),
            "candles": len(train_data)
        },
        "test_period": {
            "start": str(test_data["timestamp"].min()),
            "end": str(test_data["timestamp"].max()),
            "candles": len(test_data)
        },
        "train_report": train_report,
        "test_report": test_report,
        "data_leakage_checks": leakage_report
    }
