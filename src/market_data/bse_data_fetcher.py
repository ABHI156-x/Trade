"""
Stage 21 – BSE Historical Data Fetcher
Fetches OHLCV data from Yahoo Finance for BSE-listed stocks (.BO suffix).
"""

import pandas as pd
from src.market_data.nse_data_fetcher import _normalise


def fetch_bse_ohlcv(
    symbol: str,
    start,
    end,
    interval: str = "5m"
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data for a BSE symbol.

    Parameters
    ----------
    symbol   : BSE ticker without suffix, e.g. "RELIANCE"
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
    ticker = f"{symbol}.BO"

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

    return _normalise(raw, symbol, exchange="BSE")
