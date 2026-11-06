"""
Stage 21 – NSE Historical Data Fetcher
Fetches OHLCV data from Yahoo Finance for NSE-listed stocks (.NS suffix).
Returns a DataFrame in the project's standard schema.
"""

import pandas as pd


def fetch_nse_ohlcv(
    symbol: str,
    start,
    end,
    interval: str = "5m"
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data for an NSE symbol.

    Parameters
    ----------
    symbol   : NSE ticker without suffix, e.g. "RELIANCE"
    start    : date-like (str or datetime.date) – inclusive start
    end      : date-like – inclusive end
    interval : yfinance interval string, e.g. "5m", "1d"

    Returns
    -------
    DataFrame with columns:
        timestamp, symbol, exchange, open, high, low, close, volume
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError(
            "yfinance is required for live data. "
            "Install it with: pip install yfinance"
        )

    symbol = symbol.strip().upper()
    ticker = f"{symbol}.NS"

    raw = yf.download(
        ticker,
        start=str(start),
        end=str(end),
        interval=interval,
        progress=False,
        auto_adjust=True
    )

    if raw is None or raw.empty:
        raise ValueError(
            f"No data returned for {ticker} "
            f"({start} to {end}, interval={interval})"
        )

    df = _normalise(raw, symbol, exchange="NSE")
    return df


def _normalise(raw: pd.DataFrame, symbol: str, exchange: str) -> pd.DataFrame:
    """Convert a yfinance DataFrame to the project schema."""
    df = raw.copy()

    # yfinance may return MultiIndex columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    rename_map = {
        "date": "timestamp",
        "datetime": "timestamp",
        "adj_close": "close",
    }
    df = df.rename(columns=rename_map)

    df.index.name = "timestamp"
    df = df.reset_index()

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(
        "Asia/Kolkata"
    ).dt.tz_localize(None)

    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0).astype(int)
    df["symbol"] = symbol
    df["exchange"] = exchange

    return df[["timestamp", "symbol", "exchange", "open", "high", "low", "close", "volume"]]
