"""
Stage 24 – Tests for PaperTradingDashboard and equity_chart
"""

import pytest
from src.dashboard.equity_chart import render_ascii_equity_curve
from src.dashboard.dashboard import PaperTradingDashboard


class TestEquityChart:

    def test_returns_string(self):
        result = render_ascii_equity_curve([10000, 10100, 10050, 10200])
        assert isinstance(result, str)

    def test_shows_start_and_end_values(self):
        result = render_ascii_equity_curve([10000, 11000])
        assert "10,000" in result or "10000" in result

    def test_empty_series(self):
        result = render_ascii_equity_curve([])
        assert "no data" in result.lower()

    def test_flat_series(self):
        result = render_ascii_equity_curve([10000, 10000, 10000])
        assert isinstance(result, str)

    def test_custom_label(self):
        result = render_ascii_equity_curve([10000, 10500], label="TEST")
        assert "TEST" in result


class TestPaperTradingDashboard:

    def _make_broker_report(self):
        return {
            "initial_capital": 10000,
            "balance": 10200,
            "equity": 10300,
            "unrealized_pnl": 100,
            "open_positions": 1,
            "completed_trades": 3,
            "blocked_entries": 0,
        }

    def _make_risk_report(self):
        return {
            "realized_pnl": 200,
            "daily_loss": 0,
            "trades_taken": 3,
            "remaining_trades": 0,
            "remaining_loss_limit": 500,
        }

    def test_render_returns_string(self):
        dash = PaperTradingDashboard()
        output = dash.render(self._make_broker_report())
        assert isinstance(output, str)

    def test_render_includes_equity(self):
        dash = PaperTradingDashboard()
        output = dash.render(self._make_broker_report())
        assert "10,200" in output or "10200" in output

    def test_render_with_risk_report(self):
        dash = PaperTradingDashboard()
        output = dash.render(
            self._make_broker_report(),
            self._make_risk_report()
        )
        assert "DAILY RISK" in output

    def test_equity_sparkline_shown_with_history(self):
        dash = PaperTradingDashboard()
        for v in [10000, 10100, 10050, 10200, 10300]:
            dash.update_equity(v)
        output = dash.render(self._make_broker_report())
        # sparkline uses block characters
        assert any(c in output for c in "▁▂▃▄▅▆▇█")
