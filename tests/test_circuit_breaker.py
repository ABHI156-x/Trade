"""
Stage 23 – Tests for IndexCircuitBreaker
"""

import pytest
from src.risk.circuit_breaker import IndexCircuitBreaker


class TestCircuitBreakerNoTrigger:

    def test_no_trigger_within_threshold(self):
        cb = IndexCircuitBreaker(index_open_price=22000)
        result = cb.check(22000 * 0.95)   # 5 % fall – below 10 %
        assert not result["triggered"]
        assert result["halt_minutes"] == 0

    def test_positive_move_no_trigger(self):
        cb = IndexCircuitBreaker(index_open_price=22000)
        result = cb.check(23000)           # market up
        assert not result["triggered"]


class TestCircuitBreaker10Pct:

    def test_triggers_at_10_pct(self):
        cb = IndexCircuitBreaker(index_open_price=22000)
        result = cb.check(22000 * 0.90)   # exactly 10 %
        assert result["triggered"]
        assert result["threshold"] == 0.10
        assert result["halt_minutes"] == 45


class TestCircuitBreaker15Pct:

    def test_triggers_at_15_pct(self):
        cb = IndexCircuitBreaker(index_open_price=22000)
        result = cb.check(22000 * 0.85)
        assert result["triggered"]
        assert result["threshold"] == 0.15
        assert result["halt_minutes"] == 105


class TestCircuitBreaker20Pct:

    def test_triggers_at_20_pct(self):
        cb = IndexCircuitBreaker(index_open_price=22000)
        result = cb.check(22000 * 0.80)
        assert result["triggered"]
        assert result["threshold"] == 0.20
        assert result["halt_minutes"] == "remainder_of_day"


class TestCircuitBreakerEdgeCases:

    def test_invalid_open_price_raises(self):
        with pytest.raises(ValueError):
            IndexCircuitBreaker(index_open_price=0)

    def test_invalid_current_price_raises(self):
        cb = IndexCircuitBreaker(index_open_price=22000)
        with pytest.raises(ValueError):
            cb.check(0)

    def test_reset_day(self):
        cb = IndexCircuitBreaker(index_open_price=22000)
        cb.check(22000 * 0.85)   # trigger 15 %
        cb.reset_day(21000)
        assert cb.index_open_price == 21000
        assert not cb.triggered_thresholds

    def test_is_halted_convenience(self):
        cb = IndexCircuitBreaker(index_open_price=22000)
        assert not cb.is_halted(22000 * 0.95)
        assert cb.is_halted(22000 * 0.85)
