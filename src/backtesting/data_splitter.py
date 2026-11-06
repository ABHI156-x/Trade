
import pandas as pd


def split_market_data(df, train_ratio=0.70):

    if df.empty:
        raise ValueError("Market data cannot be empty.")

    if not 0 < train_ratio < 1:
        raise ValueError("train_ratio must be between 0 and 1.")

    required_columns = ["timestamp", "symbol"]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(f"Missing column: {column}")

    data = df.copy()

    data["timestamp"] = pd.to_datetime(
        data["timestamp"],
        errors="coerce"
    )

    if data["timestamp"].isna().any():
        raise ValueError("Invalid timestamps detected.")

    timestamps = sorted(data["timestamp"].unique())

    if len(timestamps) < 2:
        raise ValueError("At least two unique timestamps are required.")

    split_index = int(len(timestamps) * train_ratio)
    split_index = max(1, min(split_index, len(timestamps) - 1))

    split_timestamp = timestamps[split_index]

    train_data = data[
        data["timestamp"] < split_timestamp
    ].copy()

    test_data = data[
        data["timestamp"] >= split_timestamp
    ].copy()

    train_data = train_data.sort_values(
        ["timestamp", "symbol"]
    ).reset_index(drop=True)

    test_data = test_data.sort_values(
        ["timestamp", "symbol"]
    ).reset_index(drop=True)

    return train_data, test_data
