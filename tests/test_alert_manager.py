"""
Stage 25 – Tests for AlertManager and ConsoleNotifier
"""

import pytest
from unittest.mock import MagicMock
from src.alerts.alert_manager import AlertManager
from src.alerts.console_notifier import ConsoleNotifier


class TestAlertManager:

    def test_signal_alert_recorded(self):
        am = AlertManager()
        am.signal_alert("RELIANCE", "EMA_CROSSOVER")
        history = am.get_history()
        assert len(history) == 1
        assert "RELIANCE" in history[0]["message"]

    def test_risk_alert_level_warning(self):
        am = AlertManager()
        am.risk_alert("Daily loss limit reached")
        history = am.get_history(level="WARNING")
        assert len(history) == 1
        assert "RISK ALERT" in history[0]["message"]

    def test_trade_alert_close(self):
        am = AlertManager()
        trade = {"symbol": "TCS", "entry": 3500, "exit": 3600, "net_pnl": 250.0}
        am.trade_alert(trade)
        assert len(am.get_history()) == 1

    def test_system_alert_level_error(self):
        am = AlertManager()
        am.system_alert("Data feed failed")
        assert am.get_history(level="ERROR")[0]["level"] == "ERROR"

    def test_dispatches_to_notifier(self):
        mock_notifier = MagicMock()
        am = AlertManager(notifiers=[mock_notifier])
        am.signal_alert("INFY", "BREAKOUT")
        mock_notifier.send.assert_called_once()

    def test_notifier_failure_does_not_raise(self):
        bad_notifier = MagicMock()
        bad_notifier.send.side_effect = RuntimeError("boom")
        am = AlertManager(notifiers=[bad_notifier])
        am.signal_alert("WIPRO", "TEST")        # should not raise
        assert len(am.get_history()) == 1

    def test_filter_by_level(self):
        am = AlertManager()
        am.signal_alert("X", "TEST")
        am.risk_alert("Y")
        info_only = am.get_history(level="INFO")
        assert all(e["level"] == "INFO" for e in info_only)


class TestConsoleNotifier:

    def test_returns_formatted_string(self, capsys):
        cn = ConsoleNotifier()
        result = cn.send("Test message", "INFO")
        captured = capsys.readouterr().out
        assert "Test message" in captured
        assert "INFO" in captured

    def test_also_logs_to_logger(self):
        mock_logger = MagicMock()
        cn = ConsoleNotifier(logger=mock_logger)
        cn.send("Logged message", "WARNING")
        mock_logger.warning.assert_called_once_with("Logged message")
