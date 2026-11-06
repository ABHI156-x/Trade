def validate_market_data(df):

    errors = []

    required = [
        "timestamp",
        "symbol",
        "exchange",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    if df.empty:
        errors.append("Dataset is empty")
        return errors

    if df[required].isnull().any().any():
        errors.append("Missing values found")

    if df.duplicated(
        subset=["symbol", "timestamp"]
    ).any():
        errors.append("Duplicate candles found")

    invalid_prices = (
        (df["high"] < df["low"]) |
        (df["high"] < df["open"]) |
        (df["high"] < df["close"]) |
        (df["low"] > df["open"]) |
        (df["low"] > df["close"]) |
        (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
    )

    if invalid_prices.any():
        errors.append("Invalid OHLC prices found")

    if (df["volume"] < 0).any():
        errors.append("Negative volume found")

    if not df["exchange"].isin(["NSE", "BSE"]).all():
        errors.append("Invalid exchange found")

    return errors