
import pandas as pd

from src.analysis.indicators import calculate_all_indicators
from src.analysis.signals import generate_signal


def calculate_score(latest):

    bullish_score = 0
    bearish_score = 0

    # EMA trend: 30 points
    if latest["EMA_9"] > latest["EMA_21"]:
        bullish_score += 30
    elif latest["EMA_9"] < latest["EMA_21"]:
        bearish_score += 30

    # RSI momentum: 25 points
    if latest["RSI_14"] > 50:
        bullish_score += 25
    elif latest["RSI_14"] < 50:
        bearish_score += 25

    # MACD momentum: 25 points
    if latest["MACD"] > latest["MACD_SIGNAL"]:
        bullish_score += 25
    elif latest["MACD"] < latest["MACD_SIGNAL"]:
        bearish_score += 25

    # Volume confirmation: 20 points
    if latest["volume"] > latest["VOLUME_SMA_20"]:
        if bullish_score > bearish_score:
            bullish_score += 20
        elif bearish_score > bullish_score:
            bearish_score += 20

    return bullish_score, bearish_score


def scan_stocks(df):

    results = []

    for symbol, stock_data in df.groupby("symbol"):

        stock_data = stock_data.sort_values("timestamp").copy()

        analyzed_data = calculate_all_indicators(stock_data)

        latest = analyzed_data.iloc[-1]

        signal = generate_signal(analyzed_data)

        if pd.isna(latest["RSI_14"]) or pd.isna(latest["VOLUME_SMA_20"]):

            bullish_score = 0
            bearish_score = 0

        else:

            bullish_score, bearish_score = calculate_score(latest)

        score = max(bullish_score, bearish_score)

        results.append({
            "symbol": symbol,
            "exchange": latest["exchange"],
            "close": latest["close"],
            "ema_9": round(latest["EMA_9"], 2),
            "ema_21": round(latest["EMA_21"], 2),
            "rsi": round(latest["RSI_14"], 2) if pd.notna(latest["RSI_14"]) else None,
            "signal": signal,
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "score": score,
            "candles": len(stock_data)
        })

    report = pd.DataFrame(results)

    if not report.empty:
        report = report.sort_values(
            by="score",
            ascending=False
        ).reset_index(drop=True)

    return report
