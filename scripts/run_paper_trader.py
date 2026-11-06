#!/usr/bin/env python
"""
Stage 28 – Deployment Launcher: Paper Trading Runner
CLI command to run real-time or simulated paper trading.
"""

import os
import sys
import time
import signal
import argparse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.market_data.websocket_feed import SimulatedWebSocketFeed, LiveBrokerWebSocketFeed
from src.market_data.data_loader import load_market_data
from src.paper_trading.live_paper_trader import LivePaperTrader
from src.dashboard.dashboard import PaperTradingDashboard
from src.alerts.alert_manager import AlertManager
from src.alerts.console_notifier import ConsoleNotifier
from src.utils.system_logger import get_system_logger


logger = get_system_logger("logs/paper_trader.log")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Indian Day Trader - Real-Time & Replay Paper Trading Launcher"
    )
    parser.add_argument(
        "--mode",
        choices=["simulated", "replay", "live"],
        default="simulated",
        help="Trading feed mode: 'simulated' (synthetic ticks), 'replay' (from CSV), or 'live' (broker WebSocket)"
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default="RELIANCE,TCS,INFY,HDFCBANK",
        help="Comma-separated NSE symbols"
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=10000.0,
        help="Initial capital in INR (default: 10000)"
    )
    parser.add_argument(
        "--risk-per-trade",
        type=float,
        default=100.0,
        help="Risk per trade in INR (default: 100)"
    )
    parser.add_argument(
        "--max-daily-loss",
        type=float,
        default=500.0,
        help="Maximum daily loss threshold in INR (default: 500)"
    )
    parser.add_argument(
        "--max-trades",
        type=int,
        default=3,
        help="Maximum intraday trades allowed per day (default: 3)"
    )
    parser.add_argument(
        "--data-file",
        type=str,
        default="data/sample_nse_5m.csv",
        help="Path to CSV data file for 'replay' mode"
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=5.0,
        help="Simulation / replay speed multiplier (default: 5.0)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=0,
        help="Duration in seconds to run (0 runs indefinitely until Ctrl+C)"
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        default=True,
        help="Display terminal ASCII dashboard"
    )
    parser.add_argument(
        "--journal",
        type=str,
        default="data/trade_journal.csv",
        help="Path to record executed paper trades"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    print("\n" + "=" * 65)
    print("      INDIAN DAY TRADER - PAPER TRADING LAUNCHER")
    print("=" * 65)
    print(f"Mode              : {args.mode.upper()}")
    print(f"Symbols           : {', '.join(symbols)}")
    print(f"Initial Capital   : ₹{args.capital:,.2f}")
    print(f"Risk Per Trade    : ₹{args.risk_per_trade:,.2f}")
    print(f"Max Daily Loss    : ₹{args.max_daily_loss:,.2f}")
    print(f"Max Daily Trades  : {args.max_trades}")
    print(f"Trade Journal     : {args.journal}")
    print("=" * 65 + "\n")

    # 1. Setup Feed
    if args.mode == "replay":
        data_path = Path(args.data_file)
        if not data_path.exists():
            print(f"Error: Data file '{args.data_file}' not found.")
            sys.exit(1)
        df = load_market_data(str(data_path))
        feed = SimulatedWebSocketFeed(
            timeframe_minutes=5,
            tick_interval_sec=0.1,
            speed_factor=args.speed,
            historical_df=df
        )
    elif args.mode == "live":
        api_key = os.getenv("BROKER_API_KEY", "")
        access_token = os.getenv("BROKER_ACCESS_TOKEN", "")
        broker_name = os.getenv("BROKER_NAME", "zerodha")
        if not api_key or not access_token:
            print("Warning: BROKER_API_KEY or BROKER_ACCESS_TOKEN not set in environment.")
            print("Falling back to simulated real-time feed for testing.\n")
            feed = SimulatedWebSocketFeed(timeframe_minutes=5, tick_interval_sec=0.5, speed_factor=args.speed)
        else:
            feed = LiveBrokerWebSocketFeed(broker_name=broker_name, api_key=api_key, access_token=access_token)
    else:  # simulated
        feed = SimulatedWebSocketFeed(
            timeframe_minutes=5,
            tick_interval_sec=0.5,
            speed_factor=args.speed
        )

    # 2. Setup Notifiers & Dashboard
    alert_mgr = AlertManager(notifiers=[ConsoleNotifier()])
    dashboard = PaperTradingDashboard() if args.dashboard else None

    # 3. Setup Trader
    trader = LivePaperTrader(
        feed=feed,
        symbols=symbols,
        initial_capital=args.capital,
        risk_per_trade=args.risk_per_trade,
        max_daily_loss=args.max_daily_loss,
        max_trades_per_day=args.max_trades,
        journal_path=args.journal,
        alert_manager=alert_mgr,
        dashboard=dashboard,
        enforce_market_hours=False
    )

    # Handle Ctrl+C gracefully
    def handle_signal(sig, frame):
        print("\n[Shutdown] Stopping paper trader gracefully...")
        trader.stop()
        _print_final_summary(trader, dashboard)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)

    # 4. Start Trader
    trader.start()
    print("Paper trading engine is running. Press Ctrl+C to terminate.")

    start_time = time.time()
    try:
        while True:
            time.sleep(2.0)
            if args.dashboard and dashboard:
                status = trader.get_status()
                dashboard.render(status["broker"], status["risk"])

            if args.duration > 0 and (time.time() - start_time) >= args.duration:
                print(f"\n[Completed] Duration of {args.duration}s reached.")
                break
    except KeyboardInterrupt:
        pass
    finally:
        trader.stop()
        _print_final_summary(trader, dashboard)


def _print_final_summary(trader, dashboard):
    status = trader.get_status()
    broker_rep = status["broker"]
    print("\n" + "=" * 65)
    print("                 FINAL SESSION SUMMARY")
    print("=" * 65)
    print(f"Ending Balance    : ₹{broker_rep.get('balance', 0):,.2f}")
    print(f"Committed Capital : ₹{broker_rep.get('committed_capital', 0):,.2f}")
    print(f"Realized P&L      : ₹{broker_rep.get('realized_pnl', 0):,.2f}")
    print(f"Unrealized P&L    : ₹{broker_rep.get('unrealized_pnl', 0):,.2f}")
    print(f"Total Trades      : {broker_rep.get('total_trades', 0)}")
    print(f"Open Positions    : {len(broker_rep.get('positions', {}))}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
