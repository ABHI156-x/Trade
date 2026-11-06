"""
Stage 28 – Pre-Market Tasks
Runs before the trading session: download market data and run quality checks.
"""

import json
from pathlib import Path
from datetime import date


def run_pre_market_tasks(
    symbols=None,
    data_dir="data",
    exchange="NSE",
    logger=None
):
    """
    Execute pre-market preparation tasks:
      1. Verify data directory exists
      2. Download historical data for configured symbols (if yfinance available)
      3. Run data quality checks on available CSV data
      4. Log summary

    Parameters
    ----------
    symbols  : list of str – ticker symbols to download data for
    data_dir : str – path to data directory
    exchange : str – "NSE" or "BSE"
    logger   : logging.Logger – system logger

    Returns
    -------
    dict with status summary
    """
    symbols = symbols or ["RELIANCE", "INFY", "TCS"]
    today   = date.today()

    def log(msg, level="info"):
        if logger:
            getattr(logger, level)(msg)
        print(f"[PRE-MARKET] {msg}")

    log(f"Pre-market tasks starting for {today}")

    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)

    results = {}

    # Try to download fresh data
    try:
        from src.market_data.nse_data_fetcher import fetch_nse_ohlcv
        from src.market_data.bse_data_fetcher import fetch_bse_ohlcv

        fetcher = fetch_nse_ohlcv if exchange == "NSE" else fetch_bse_ohlcv

        for symbol in symbols:
            try:
                df = fetcher(symbol, today, today, interval="5m")
                out_file = data_path / f"{symbol}_{today}.csv"
                df.to_csv(out_file, index=False)
                log(f"Downloaded {symbol}: {len(df)} rows -> {out_file.name}")
                results[symbol] = {"status": "OK", "rows": len(df)}
            except Exception as exc:
                log(f"Download failed for {symbol}: {exc}", "warning")
                results[symbol] = {"status": "FAILED", "error": str(exc)}

    except ImportError:
        log("yfinance not available; skipping live download", "warning")

    # Run quality check on sample data if available
    sample_csv = data_path / "sample_nse_5m.csv"

    if sample_csv.exists():
        try:
            from src.market_data.data_quality import check_market_data_quality
            import pandas as pd

            df = pd.read_csv(sample_csv)
            report = check_market_data_quality(df, exchange=exchange)
            log(
                f"Data quality: {report['total_rows']} rows, "
                f"{report['issue_count']} issues"
            )
        except Exception as exc:
            log(f"Quality check failed: {exc}", "warning")

    log("Pre-market tasks complete")
    return {"date": str(today), "symbols": results}
