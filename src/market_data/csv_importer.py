
import pandas as pd
from pathlib import Path


REQUIRED_COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume"
]


def import_historical_csv(file_path, symbol=None, exchange="NSE"):

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    exchange = exchange.upper()

    if exchange not in ["NSE", "BSE"]:
        raise ValueError("Exchange must be NSE or BSE.")

    df = pd.read_csv(path)

    df.columns = df.columns.str.strip().str.lower()

    has_symbol_column = "symbol" in df.columns
    has_exchange_column = "exchange" in df.columns

    required = REQUIRED_COLUMNS.copy()

    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    numeric_columns = [
        "open", "high", "low", "close", "volume"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    if df[REQUIRED_COLUMNS].isnull().any().any():
        raise ValueError("CSV contains invalid or missing values.")

    if (df[numeric_columns] < 0).any().any():
        raise ValueError("Negative values are not allowed.")

    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("OHLC prices must be positive.")

    invalid_ohlc = (
        (df["high"] < df[["open", "close", "low"]].max(axis=1))
        |
        (df["low"] > df[["open", "close", "high"]].min(axis=1))
    )

    if invalid_ohlc.any():
        raise ValueError("Invalid OHLC candle detected.")

    if has_symbol_column:

        df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()

        if df["symbol"].eq("").any():
            raise ValueError("Empty stock symbol detected.")

        if symbol is not None:
            df = df[df["symbol"] == symbol.strip().upper()].copy()

            if df.empty:
                raise ValueError(f"No data found for symbol: {symbol}")

    else:

        if not symbol:
            raise ValueError("Symbol is required when CSV has no symbol column.")

        df["symbol"] = symbol.strip().upper()

    if has_exchange_column:

        df["exchange"] = df["exchange"].astype(str).str.strip().str.upper()

        if not df["exchange"].isin(["NSE", "BSE"]).all():
            raise ValueError("Invalid exchange found in CSV.")

    else:

        df["exchange"] = exchange

    duplicate_columns = ["symbol", "timestamp"]

    if df.duplicated(subset=duplicate_columns).any():
        raise ValueError("Duplicate symbol and timestamp candles detected.")

    df = df.sort_values(
        ["symbol", "timestamp"]
    ).reset_index(drop=True)

    return df[
        [
            "timestamp", "symbol", "exchange",
            "open", "high", "low", "close", "volume"
        ]
    ]
