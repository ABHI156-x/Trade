"""
Historical Data Source Verifier & Limitation Checker.

Provides validation, diagnostics, and limitation awareness for Yahoo Finance
and other market data providers used for NSE/BSE historical data.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, Tuple
import pandas as pd


# yfinance API hard boundaries for intraday intervals
INTERVAL_LIMITS_DAYS = {
    "1m": 30,
    "2m": 60,
    "5m": 60,
    "15m": 60,
    "30m": 60,
    "60m": 730,
    "90m": 60,
    "1h": 730,
    "1d": 365 * 30,
}


class DataSourceVerifier:
    """
    Verifies queries before sending to upstream data sources like yfinance,
    preventing silent failures and diagnosing known API limits.
    """

    @staticmethod
    def validate_date_range(start_date: Any, end_date: Any, interval: str = "5m") -> Tuple[bool, str]:
        """
        Check if the requested date range and interval comply with Yahoo Finance limits.
        """
        interval = interval.lower()
        if interval not in INTERVAL_LIMITS_DAYS:
            return False, f"Unsupported interval '{interval}'. Supported: {list(INTERVAL_LIMITS_DAYS.keys())}"

        try:
            start_dt = pd.to_datetime(start_date).date()
            end_dt = pd.to_datetime(end_date).date()
        except Exception as e:
            return False, f"Invalid date format: {e}"

        if start_dt > end_dt:
            return False, f"Start date ({start_dt}) cannot be after end date ({end_dt})"

        today = date.today()
        max_days = INTERVAL_LIMITS_DAYS[interval]
        earliest_allowed = today - timedelta(days=max_days)

        if start_dt < earliest_allowed:
            return (
                False,
                f"yfinance limit: interval '{interval}' only supports history within the last {max_days} days "
                f"(requested {start_dt}, earliest allowed {earliest_allowed})"
            )

        return True, "Valid date range"

    @staticmethod
    def get_source_limitations() -> Dict[str, Any]:
        """
        Returns structured documentation of historical data limitations.
        """
        return {
            "source": "Yahoo Finance (via yfinance)",
            "exchange_suffixes": {"NSE": ".NS", "BSE": ".BO"},
            "intraday_limitations": {
                "1m": "Last 30 calendar days maximum",
                "5m": "Last 60 calendar days maximum",
                "15m": "Last 60 calendar days maximum",
                "1h": "Last 730 calendar days maximum",
                "1d": "Full historical series available"
            },
            "delays_and_rate_limits": {
                "real_time": "Delayed by 1-15 minutes or snapshot only; NOT a live streaming WebSocket",
                "rate_limits": "Yahoo Finance frequently throttles or blocks IP addresses on excessive requests",
                "tick_size": "Does not provide tick-by-tick (L1/L2) order book depth",
                "official_circulars": "Occasional discrepancies in corporate actions vs official NSE/BSE circulars"
            },
            "recommended_production_source": "Official Broker APIs (e.g., Zerodha Kite Connect, Angel One SmartAPI, DhanHQ)"
        }
