"""
Stage 23 – Tests for AdvancedRiskGuard
"""

import pytest
from src.risk.advanced_risk_guard import AdvancedRiskGuard


class TestExposureLimit:

    def test_blocks_when_exposure_exceeded(self):
        guard = AdvancedRiskGuard(
            total_capital=10000,
            max_exposure_percent=0.5
        )
        allowed, reason = guard.can_take_trade(current_exposure=5001)
        assert not allowed
        assert "Exposure" in reason

    def test_allows_when_exposure_within_limit(self):
        guard = AdvancedRiskGuard(
            total_capital=10000,
            max_exposure_percent=0.5
        )
        allowed, _ = guard.can_take_trade(current_exposure=4999)
        assert allowed

    def test_invalid_exposure_percent_raises(self):
        with pytest.raises(ValueError):
            AdvancedRiskGuard(max_exposure_percent=1.5)


class TestConsecutiveLossCircuitBreaker:

    def test_blocks_after_consecutive_losses(self):
        guard = AdvancedRiskGuard(max_consecutive_losses=2)
        guard.record_trade(-100)
        guard.record_trade(-100)
        allowed, reason = guard.can_take_trade()
        assert not allowed
        assert "Circuit breaker" in reason

    def test_resets_streak_on_win(self):
        guard = AdvancedRiskGuard(max_consecutive_losses=2, max_trades=5)
        guard.record_trade(-100)
        guard.record_trade(50)   # win resets streak
        guard.record_trade(-100)
        allowed, _ = guard.can_take_trade()
        assert allowed


class TestSectorCaps:

    def test_blocks_when_sector_cap_reached(self):
        guard = AdvancedRiskGuard(sector_caps={"BANK": 1})
        guard.record_trade(100, sector="BANK")
        allowed, reason = guard.can_take_trade(sector="BANK")
        assert not allowed
        assert "BANK" in reason

    def test_allows_different_sector(self):
        guard = AdvancedRiskGuard(sector_caps={"BANK": 1})
        guard.record_trade(100, sector="BANK")
        allowed, _ = guard.can_take_trade(sector="IT")
        assert allowed

    def test_uncapped_sector_always_allowed(self):
        guard = AdvancedRiskGuard(sector_caps={})
        allowed, _ = guard.can_take_trade(sector="PHARMA")
        assert allowed


class TestReset:

    def test_reset_clears_consecutive_losses(self):
        guard = AdvancedRiskGuard(max_consecutive_losses=2)
        guard.record_trade(-100)
        guard.record_trade(-100)
        guard.reset()
        allowed, _ = guard.can_take_trade()
        assert allowed

    def test_reset_clears_sector_counts(self):
        guard = AdvancedRiskGuard(sector_caps={"BANK": 1})
        guard.record_trade(100, sector="BANK")
        guard.reset()
        allowed, _ = guard.can_take_trade(sector="BANK")
        assert allowed


class TestReport:

    def test_report_includes_advanced_fields(self):
        guard = AdvancedRiskGuard()
        report = guard.get_report()
        assert "consecutive_losses" in report
        assert "max_consecutive_losses" in report
        assert "sector_counts" in report
