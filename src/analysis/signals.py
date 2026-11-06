def generate_signal(df):

    latest = df.iloc[-1]

    required = [
        "EMA_9",
        "EMA_21",
        "RSI_14",
        "MACD",
        "MACD_SIGNAL"
    ]

    if latest[required].isna().any():
        return "INSUFFICIENT DATA"

    bullish_points = 0
    bearish_points = 0

    # EMA comparison
    if latest["EMA_9"] > latest["EMA_21"]:
        bullish_points += 1
    else:
        bearish_points += 1

    # RSI
    if latest["RSI_14"] > 50:
        bullish_points += 1
    elif latest["RSI_14"] < 50:
        bearish_points += 1

    # MACD
    if latest["MACD"] > latest["MACD_SIGNAL"]:
        bullish_points += 1
    else:
        bearish_points += 1

    if bullish_points >= 3:
        return "BULLISH"

    elif bearish_points >= 3:
        return "BEARISH"

    return "NEUTRAL"