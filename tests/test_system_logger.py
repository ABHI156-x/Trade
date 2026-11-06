"""
Stage 26 – Tests for system_logger and health_monitor
"""

import pytest
import logging
from pathlib import Path
from datetime import datetime, timedelta

from src.utils.system_logger import get_system_logger, close_system_logger
from src.monitoring.health_monitor import HealthMonitor


class TestSystemLogger:

    def test_returns_logger(self, tmp_path):
        log_file = tmp_path / "test_system.log"
        logger = get_system_logger(str(log_file))
        assert isinstance(logger, logging.Logger)
        close_system_logger()

    def test_creates_log_file(self, tmp_path):
        log_file = tmp_path / "subdir" / "test.log"
        logger = get_system_logger(str(log_file))
        logger.warning("test message")
        assert log_file.exists()
        close_system_logger()

    def test_idempotent_multiple_calls(self, tmp_path):
        log_file = tmp_path / "idem.log"
        l1 = get_system_logger(str(log_file))
        l2 = get_system_logger(str(log_file))
        assert l1 is l2
        close_system_logger()

    def test_writes_message(self, tmp_path):
        log_file = tmp_path / "write_test.log"
        logger = get_system_logger(str(log_file))
        logger.error("integration test error")
        for h in logger.handlers:
            h.flush()
        assert "integration test error" in log_file.read_text(encoding="utf-8")
        close_system_logger()


class TestHealthMonitor:

    def test_initial_no_candle_unhealthy(self):
        hm = HealthMonitor()
        result = hm.check_candle_age()
        assert not result["ok"]
        assert "No candle" in result["issue"]

    def test_fresh_candle_healthy(self):
        hm = HealthMonitor(max_candle_age_seconds=300)
        hm.record_candle(datetime.now())
        result = hm.check_candle_age()
        assert result["ok"]

    def test_stale_candle_unhealthy(self):
        hm = HealthMonitor(max_candle_age_seconds=60)
        old_time = datetime.now() - timedelta(seconds=120)
        hm.record_candle(old_time)
        result = hm.check_candle_age()
        assert not result["ok"]
        assert "stale" in result["issue"].lower()

    def test_positions_within_limit(self):
        hm = HealthMonitor(max_open_positions=5)
        result = hm.check_positions(3)
        assert result["ok"]

    def test_positions_exceeded(self):
        hm = HealthMonitor(max_open_positions=5)
        result = hm.check_positions(6)
        assert not result["ok"]

    def test_get_report_healthy(self):
        hm = HealthMonitor()
        hm.record_candle(datetime.now())
        report = hm.get_report(open_positions=2)
        assert "healthy" in report
        assert "uptime_seconds" in report

    def test_invalid_max_candle_age_raises(self):
        with pytest.raises(ValueError):
            HealthMonitor(max_candle_age_seconds=0)

    def test_invalid_max_positions_raises(self):
        with pytest.raises(ValueError):
            HealthMonitor(max_open_positions=0)
