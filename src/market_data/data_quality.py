
import pandas as pd


REQUIRED_COLUMNS = [
    "timestamp",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume"
]


def check_market_data_quality(df, interval_minutes=5, exchange="NSE"):

    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be positive.")

    exchange = exchange.upper()

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    if df.empty:
        return {
            "total_rows": 0,
            "total_symbols": 0,
            "issue_count": 0,
            "issues": []
        }

    data = df.copy()
    issues = []

    data["timestamp"] = pd.to_datetime(
        data["timestamp"],
        errors="coerce"
    )

    numeric_columns = [
        "open", "high", "low", "close", "volume"
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )

    def add_issue(symbol, issue_type, details):
        issues.append({
            "symbol": str(symbol),
            "issue": issue_type,
            "details": str(details)
        })

    # Check missing values
    for column in REQUIRED_COLUMNS:
        invalid_rows = data[data[column].isna()]

        for index in invalid_rows.index:
            add_issue(
                data.loc[index, "symbol"],
                "MISSING_OR_INVALID_VALUE",
                f"Invalid value in {column}, row {index}"
            )

    valid = data.dropna(
        subset=REQUIRED_COLUMNS
    ).copy()

    # Check duplicate timestamps
    duplicates = valid.duplicated(
        subset=["symbol", "timestamp"],
        keep=False
    )

    for _, row in valid[duplicates].iterrows():
        add_issue(
            row["symbol"],
            "DUPLICATE_TIMESTAMP",
            row["timestamp"]
        )

    # Check price and volume values
    for _, row in valid.iterrows():

        symbol = row["symbol"]

        if min(
            row["open"],
            row["high"],
            row["low"],
            row["close"]
        ) <= 0:
            add_issue(
                symbol,
                "NON_POSITIVE_PRICE",
                row["timestamp"]
            )

        if (
            row["high"] < max(row["open"], row["close"])
            or row["low"] > min(row["open"], row["close"])
            or row["high"] < row["low"]
        ):
            add_issue(
                symbol,
                "INVALID_OHLC",
                row["timestamp"]
            )

        if row["volume"] < 0:
            add_issue(
                symbol,
                "NEGATIVE_VOLUME",
                row["timestamp"]
            )

        current_time = row["timestamp"].time()

        if not (
            pd.Timestamp("09:15").time()
            <= current_time
            <= pd.Timestamp("15:30").time()
        ):
            add_issue(
                symbol,
                "OUTSIDE_MARKET_SESSION",
                row["timestamp"]
            )

    # Detect missing candles within a trading session.
    # Gaps that cross overnight or known holidays are excluded.
    try:
        from src.utils.market_calendar import is_trading_day
        _calendar_available = True
    except ImportError:
        _calendar_available = False

    unique_data = valid.drop_duplicates(
        subset=["symbol", "timestamp"]
    )

    for (symbol, day), group in unique_data.groupby(
        ["symbol", unique_data["timestamp"].dt.date]
    ):

        # Skip non-trading days when calendar is available
        if _calendar_available and not is_trading_day(day, exchange):
            continue

        timestamps = pd.DatetimeIndex(
            group["timestamp"].sort_values()
        )

        if len(timestamps) < 2:
            continue

        expected = pd.date_range(
            start=timestamps.min(),
            end=timestamps.max(),
            freq=f"{interval_minutes}min"
        )

        missing = expected.difference(timestamps)

        for timestamp in missing:
            add_issue(
                symbol,
                "MISSING_CANDLE",
                timestamp
            )

    return {
        "total_rows": len(data),
        "total_symbols": data["symbol"].nunique(),
        "issue_count": len(issues),
        "issues": issues
    }


def print_data_quality_report(report):

    print("\n" + "=" * 50)
    print("       MARKET DATA QUALITY REPORT")
    print("=" * 50)

    print("Total rows:", report["total_rows"])
    print("Total symbols:", report["total_symbols"])
    print("Total issues:", report["issue_count"])

    if not report["issues"]:
        print("\nData quality: PASSED")
        return

    print("\nData quality: ISSUES FOUND")
    print("-" * 50)

    for issue in report["issues"]:
        print(
            f'{issue["symbol"]} | '
            f'{issue["issue"]} | '
            f'{issue["details"]}'
        )
