"""
Stage 22 – NSE / BSE Market Calendar
Provides NSE/BSE holiday lists and trading-day helpers for 2024-2025.
Used by data_quality.py to distinguish holiday gaps from missing candles.
"""

from datetime import date, timedelta
from typing import List


# ------------------------------------------------------------------ Holiday list
# Source: NSE official trading holiday schedule 2024-2025
_NSE_HOLIDAYS_2024 = {
    date(2024,  1, 22),  # Ram Mandir Prana Pratishtha (special holiday)
    date(2024,  1, 26),  # Republic Day
    date(2024,  3, 25),  # Holi
    date(2024,  3, 29),  # Good Friday
    date(2024,  4, 11),  # Id-Ul-Fitr (Ramzan Eid)
    date(2024,  4, 14),  # Dr. Ambedkar Jayanti / Ram Navami
    date(2024,  4, 17),  # Ram Navami
    date(2024,  4, 21),  # Mahavir Jayanti
    date(2024,  5,  1),  # Maharashtra Day
    date(2024,  6, 17),  # Bakri Eid
    date(2024,  7, 17),  # Muharram
    date(2024,  8, 15),  # Independence Day
    date(2024, 10,  2),  # Gandhi Jayanti / Dussehra
    date(2024, 11,  1),  # Diwali Laxmi Puja (Muhurat Trading only)
    date(2024, 11, 15),  # Gurunanak Jayanti
    date(2024, 12, 25),  # Christmas
}

_NSE_HOLIDAYS_2025 = {
    date(2025,  1, 26),  # Republic Day
    date(2025,  2, 26),  # Mahashivratri
    date(2025,  3, 14),  # Holi
    date(2025,  3, 31),  # Id-Ul-Fitr
    date(2025,  4, 10),  # Shri Ram Navami
    date(2025,  4, 14),  # Dr. Ambedkar Jayanti
    date(2025,  4, 18),  # Good Friday
    date(2025,  5,  1),  # Maharashtra Day
    date(2025,  8, 15),  # Independence Day
    date(2025,  8, 27),  # Ganesh Chaturthi
    date(2025, 10,  2),  # Gandhi Jayanti / Dussehra
    date(2025, 10, 20),  # Diwali
    date(2025, 10, 21),  # Diwali (Laxmi Puja)
    date(2025, 11,  5),  # Gurunanak Jayanti
    date(2025, 12, 25),  # Christmas
}

# BSE uses the same holidays as NSE for equity segment
_BSE_HOLIDAYS_2024 = _NSE_HOLIDAYS_2024.copy()
_BSE_HOLIDAYS_2025 = _NSE_HOLIDAYS_2025.copy()

_HOLIDAYS = {
    "NSE": _NSE_HOLIDAYS_2024 | _NSE_HOLIDAYS_2025,
    "BSE": _BSE_HOLIDAYS_2024 | _BSE_HOLIDAYS_2025,
}


# ------------------------------------------------------------------ Public API

def is_trading_day(d: date, exchange: str = "NSE") -> bool:
    """
    Return True if *d* is a valid equity trading day on *exchange*.
    Weekends and known holidays return False.
    """
    exchange = exchange.upper()

    if exchange not in _HOLIDAYS:
        raise ValueError(f"Unknown exchange: {exchange}. Use 'NSE' or 'BSE'.")

    if d.weekday() >= 5:          # Saturday=5, Sunday=6
        return False

    return d not in _HOLIDAYS[exchange]


def get_trading_days(
    start: date,
    end: date,
    exchange: str = "NSE"
) -> List[date]:
    """
    Return a sorted list of trading days between *start* and *end* (inclusive).
    """
    exchange = exchange.upper()

    if start > end:
        raise ValueError("start must be on or before end.")

    result = []
    current = start

    while current <= end:
        if is_trading_day(current, exchange):
            result.append(current)
        current += timedelta(days=1)

    return result


def next_trading_day(d: date, exchange: str = "NSE") -> date:
    """Return the next trading day after *d*."""
    candidate = d + timedelta(days=1)

    while not is_trading_day(candidate, exchange):
        candidate += timedelta(days=1)

    return candidate


def previous_trading_day(d: date, exchange: str = "NSE") -> date:
    """Return the previous trading day before *d*."""
    candidate = d - timedelta(days=1)

    while not is_trading_day(candidate, exchange):
        candidate -= timedelta(days=1)

    return candidate
