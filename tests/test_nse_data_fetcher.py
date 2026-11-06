"""
Stage 21 – Tests for NSE/BSE data fetchers.
Network calls are mocked so the tests run offline.
"""

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock


# ------------------------------------------------------------------ helpers

def _make_yf_df():
    """Minimal yfinance-style DataFrame."""
    dates = pd.date_range("2024-01-01 09:15", periods=3, freq="5min", tz="UTC")
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [101.0, 102.0, 103.0],
            "Low":  [ 99.0, 100.0, 101.0],
            "Close":[100.5, 101.5, 102.5],
            "Volume":[500, 600, 700],
        },
        index=pd.DatetimeIndex(dates, name="Datetime"),
    )


# ------------------------------------------------------------------ NSE fetcher

class TestNseDataFetcher:

    @patch("yfinance.download")
    def test_returns_correct_schema(self, mock_dl):
        mock_dl.return_value = _make_yf_df()
        from src.market_data.nse_data_fetcher import fetch_nse_ohlcv
        df = fetch_nse_ohlcv("RELIANCE", "2024-01-01", "2024-01-05")
        expected = ["timestamp", "symbol", "exchange", "open", "high", "low", "close", "volume"]
        assert list(df.columns) == expected

    @patch("yfinance.download")
    def test_symbol_and_exchange_set(self, mock_dl):
        mock_dl.return_value = _make_yf_df()
        from src.market_data.nse_data_fetcher import fetch_nse_ohlcv
        df = fetch_nse_ohlcv("TCS", "2024-01-01", "2024-01-05")
        assert (df["symbol"] == "TCS").all()
        assert (df["exchange"] == "NSE").all()

    @patch("yfinance.download")
    def test_raises_on_empty_response(self, mock_dl):
        mock_dl.return_value = pd.DataFrame()
        from src.market_data.nse_data_fetcher import fetch_nse_ohlcv
        with pytest.raises(ValueError, match="No data returned"):
            fetch_nse_ohlcv("INVALID", "2024-01-01", "2024-01-05")

    @patch("yfinance.download")
    def test_timestamps_are_naive(self, mock_dl):
        """Timestamps must be timezone-naive (IST localised and stripped)."""
        mock_dl.return_value = _make_yf_df()
        from src.market_data.nse_data_fetcher import fetch_nse_ohlcv
        df = fetch_nse_ohlcv("INFY", "2024-01-01", "2024-01-05")
        assert df["timestamp"].dt.tz is None


# ------------------------------------------------------------------ BSE fetcher

class TestBseDataFetcher:

    @patch("yfinance.download")
    def test_returns_correct_schema(self, mock_dl):
        mock_dl.return_value = _make_yf_df()
        from src.market_data.bse_data_fetcher import fetch_bse_ohlcv
        df = fetch_bse_ohlcv("RELIANCE", "2024-01-01", "2024-01-05")
        expected = ["timestamp", "symbol", "exchange", "open", "high", "low", "close", "volume"]
        assert list(df.columns) == expected

    @patch("yfinance.download")
    def test_exchange_is_bse(self, mock_dl):
        mock_dl.return_value = _make_yf_df()
        from src.market_data.bse_data_fetcher import fetch_bse_ohlcv
        df = fetch_bse_ohlcv("TCS", "2024-01-01", "2024-01-05")
        assert (df["exchange"] == "BSE").all()

    @patch("yfinance.download")
    def test_raises_on_empty_response(self, mock_dl):
        mock_dl.return_value = pd.DataFrame()
        from src.market_data.bse_data_fetcher import fetch_bse_ohlcv
        with pytest.raises(ValueError, match="No data returned"):
            fetch_bse_ohlcv("INVALID", "2024-01-01", "2024-01-05")


# ------------------------------------------------------------------ data_loader routing

class TestDataLoaderRouting:

    def test_csv_route_works(self, tmp_path):
        csv = tmp_path / "test.csv"
        data = pd.DataFrame({
            "timestamp": ["2024-01-01 09:15", "2024-01-01 09:20"],
            "symbol":    ["INFY", "INFY"],
            "exchange":  ["NSE", "NSE"],
            "open":  [100.0, 101.0],
            "high":  [101.0, 102.0],
            "low":   [ 99.0, 100.0],
            "close": [100.5, 101.5],
            "volume":[500, 600],
        })
        data.to_csv(csv, index=False)
        from src.market_data.data_loader import load_market_data
        df = load_market_data(str(csv))
        assert len(df) == 2

    def test_missing_csv_raises(self):
        from src.market_data.data_loader import load_market_data
        with pytest.raises(FileNotFoundError):
            load_market_data("nonexistent_file.csv")

    @patch("src.market_data.nse_data_fetcher.fetch_nse_ohlcv")
    def test_live_nse_route(self, mock_fetch):
        mock_fetch.return_value = pd.DataFrame(columns=[
            "timestamp", "symbol", "exchange", "open", "high", "low", "close", "volume"
        ])
        from src.market_data.data_loader import load_market_data
        load_market_data(
            "RELIANCE",
            symbol="RELIANCE",
            exchange="NSE",
            start="2024-01-01",
            end="2024-01-05"
        )
        mock_fetch.assert_called_once()

    def test_live_requires_start_end(self):
        from src.market_data.data_loader import load_market_data
        with pytest.raises(ValueError, match="start and end"):
            load_market_data("RELIANCE", exchange="NSE")
