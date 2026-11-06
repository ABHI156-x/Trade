"""
Stage 22 – Tests for market_calendar.py
"""

import pytest
from datetime import date
from src.utils.market_calendar import (
    is_trading_day,
    get_trading_days,
    next_trading_day,
    previous_trading_day,
)


class TestIsTradingDay:

    def test_weekday_is_trading_day(self):
        # 22 Jan 2024 is a Monday (also a special NSE holiday)
        # Use a regular Monday
        assert is_trading_day(date(2024, 1, 15)) is False  # holiday (Republic day week?)
        # 8 Jan 2024 – regular Monday, not a holiday
        assert is_trading_day(date(2024, 1, 8)) is True

    def test_saturday_not_trading(self):
        assert is_trading_day(date(2024, 1, 6)) is False   # Saturday

    def test_sunday_not_trading(self):
        assert is_trading_day(date(2024, 1, 7)) is False   # Sunday

    def test_republic_day_not_trading(self):
        assert is_trading_day(date(2024, 1, 26)) is False

    def test_christmas_not_trading(self):
        assert is_trading_day(date(2024, 12, 25)) is False

    def test_invalid_exchange_raises(self):
        with pytest.raises(ValueError, match="Unknown exchange"):
            is_trading_day(date(2024, 1, 8), exchange="INVALID")


class TestGetTradingDays:

    def test_returns_only_trading_days(self):
        days = get_trading_days(date(2024, 1, 1), date(2024, 1, 5))
        for d in days:
            assert is_trading_day(d)

    def test_excludes_holidays(self):
        # Republic Day 26 Jan 2024
        days = get_trading_days(date(2024, 1, 24), date(2024, 1, 29))
        assert date(2024, 1, 26) not in days

    def test_start_after_end_raises(self):
        with pytest.raises(ValueError, match="start must be on or before end"):
            get_trading_days(date(2024, 2, 1), date(2024, 1, 1))

    def test_same_day_range(self):
        days = get_trading_days(date(2024, 1, 8), date(2024, 1, 8))
        assert days == [date(2024, 1, 8)]


class TestNextPreviousTradingDay:

    def test_next_skips_weekend(self):
        # Friday -> Monday
        nxt = next_trading_day(date(2024, 1, 5))
        assert nxt == date(2024, 1, 8)

    def test_previous_skips_weekend(self):
        # Monday -> Friday
        prev = previous_trading_day(date(2024, 1, 8))
        assert prev == date(2024, 1, 5)
