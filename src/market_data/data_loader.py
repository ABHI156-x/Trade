import pandas as pd
from pathlib import Path


def load_market_data(
    source,
    symbol=None,
    exchange="NSE",
    start=None,
    end=None,
    interval="5m"
):
    """
    Load market data from a CSV file or live yfinance feed.

    Parameters
    ----------
    source   : str – path to a CSV file (must end with .csv) OR a ticker symbol
               string when fetching live data.
    symbol   : str or None – stock symbol; required for live fetch if source is
               not a CSV, or to filter a multi-symbol CSV.
    exchange : "NSE" or "BSE" – used only for live fetches.
    start    : date-like – start date for live fetch.
    end      : date-like – end date for live fetch.
    interval : yfinance interval string (default "5m").

    Returns
    -------
    DataFrame with columns:
        timestamp, symbol, exchange, open, high, low, close, volume
    """
    source = str(source)

    # ------------------------------------------------------------------ CSV path
    if source.lower().endswith(".csv"):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        df = pd.read_csv(path)

        required_columns = [
            "timestamp", "symbol", "exchange",
            "open", "high", "low", "close", "volume"
        ]

        for column in required_columns:
            if column not in df.columns:
                raise ValueError(f"Missing column: {column}")

        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        for column in ["open", "high", "low", "close", "volume"]:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        # Optionally filter to a single symbol
        if symbol is not None:
            df = df[df["symbol"].str.upper() == symbol.strip().upper()].copy()

        return df.sort_values(["symbol", "timestamp"]).reset_index(drop=True)

    # ----------------------------------------------------------------- Live path
    exchange = exchange.upper()

    if exchange not in ("NSE", "BSE"):
        raise ValueError("exchange must be 'NSE' or 'BSE'")

    if start is None or end is None:
        raise ValueError(
            "start and end dates are required for live data fetching."
        )

    ticker_symbol = symbol.strip().upper() if symbol else source.strip().upper()

    if exchange == "NSE":
        from src.market_data.nse_data_fetcher import fetch_nse_ohlcv
        return fetch_nse_ohlcv(ticker_symbol, start, end, interval)
    else:
        from src.market_data.bse_data_fetcher import fetch_bse_ohlcv
        return fetch_bse_ohlcv(ticker_symbol, start, end, interval)