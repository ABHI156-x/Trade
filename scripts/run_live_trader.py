#!/usr/bin/env python
"""
Live Trading Launcher for Indian Stock Exchanges (NSE / BSE).
Connects to official broker APIs (Zerodha Kite Connect / Angel One SmartAPI),
streams real-time market data, evaluates signals, and executes orders
through the safe OrderExecutionEngine with Kill-Switch protection.
"""

import os
import sys
import time
import signal
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env file
load_dotenv(PROJECT_ROOT / ".env")

from src.broker.base_broker import Order, OrderType, TransactionType, ProductType, OrderStatus
from src.broker.zerodha_broker import ZerodhaBroker
from src.broker.angel_one_broker import AngelOneBroker
from src.execution.order_execution_engine import OrderExecutionEngine
from src.market_data.websocket_feed import LiveBrokerWebSocketFeed, SimulatedWebSocketFeed
from src.scanner.stock_scanner import scan_stocks
from src.risk.advanced_risk_guard import AdvancedRiskGuard
from src.dashboard.dashboard import PaperTradingDashboard
from src.alerts.alert_manager import AlertManager
from src.alerts.console_notifier import ConsoleNotifier
from src.utils.market_session import is_market_session, is_entry_allowed, is_square_off_time
from src.utils.system_logger import get_system_logger


logger = get_system_logger("logs/live_trader.log")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Indian Day Trader - Live Broker Trading Launcher"
    )
    parser.add_argument(
        "--broker",
        choices=["zerodha", "angelone"],
        default=os.getenv("BROKER_NAME", "zerodha"),
        help="Broker API: 'zerodha' (Kite Connect) or 'angelone' (SmartAPI)"
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default="RELIANCE,TCS,INFY,HDFCBANK",
        help="Comma-separated NSE tickers (e.g. RELIANCE,TCS,INFY)"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Execute REAL orders on the broker. When omitted, runs in safe DRY-RUN mode."
    )
    parser.add_argument(
        "--max-order-value",
        type=float,
        default=25000.0,
        help="Fat-finger safety limit: Max INR value for a single order (default: ₹25,000)"
    )
    parser.add_argument(
        "--max-daily-turnover",
        type=float,
        default=100000.0,
        help="Safety limit: Max cumulative daily turnover in INR (default: ₹1,00,000)"
    )
    parser.add_argument(
        "--max-daily-loss",
        type=float,
        default=500.0,
        help="Hard daily loss stop threshold in INR (default: ₹500)"
    )
    parser.add_argument(
        "--max-trades",
        type=int,
        default=3,
        help="Maximum intraday trades per day (default: 3)"
    )
    parser.add_argument(
        "--risk-per-trade",
        type=float,
        default=100.0,
        help="Maximum risk amount in INR per trade (default: ₹100)"
    )
    parser.add_argument(
        "--stop-loss-pct",
        type=float,
        default=0.01,
        help="Stop loss percentage (default: 0.01 = 1 percent)"
    )
    parser.add_argument(
        "--target-pct",
        type=float,
        default=0.02,
        help="Profit target percentage (default: 0.02 = 2 percent)"
    )
    parser.add_argument(
        "--timeframe",
        type=int,
        default=5,
        help="Candle timeframe in minutes (default: 5)"
    )
    parser.add_argument(
        "--enforce-market-hours",
        action="store_true",
        default=True,
        help="Enforce NSE trading hours (09:15 to 15:30 IST)"
    )
    return parser.parse_args()


def init_broker(broker_name: str, is_mock: bool):
    """Initialize broker client with credentials from environment."""
    if broker_name == "zerodha":
        api_key = os.getenv("ZERODHA_API_KEY", os.getenv("BROKER_API_KEY", ""))
        api_secret = os.getenv("ZERODHA_API_SECRET", os.getenv("BROKER_API_SECRET", ""))
        access_token = os.getenv("ZERODHA_ACCESS_TOKEN", os.getenv("BROKER_ACCESS_TOKEN", ""))
        return ZerodhaBroker(
            api_key=api_key,
            api_secret=api_secret,
            access_token=access_token,
            is_mock=is_mock
        )
    elif broker_name == "angelone":
        api_key = os.getenv("ANGEL_API_KEY", os.getenv("BROKER_API_KEY", ""))
        client_code = os.getenv("ANGEL_CLIENT_CODE", "")
        jwt_token = os.getenv("ANGEL_JWT_TOKEN", os.getenv("BROKER_ACCESS_TOKEN", ""))
        return AngelOneBroker(
            api_key=api_key,
            client_code=client_code,
            jwt_token=jwt_token,
            is_mock=is_mock
        )
    else:
        raise ValueError(f"Unsupported broker: {broker_name}")


def main():
    args = parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    is_live = args.live
    dry_run = not is_live

    print("\n" + "=" * 65)
    print("      INDIAN DAY TRADER - LIVE BROKER EXECUTION ENGINE")
    print("=" * 65)
    print(f"Target Broker     : {args.broker.upper()}")
    print(f"Watchlist Symbols : {', '.join(symbols)}")
    print(f"Execution Mode    : {'🔴 LIVE REAL-MONEY ORDERS' if is_live else '🟢 SAFE DRY-RUN (Simulated Orders)'}")
    print(f"Max Single Order  : ₹{args.max_order_value:,.2f}")
    print(f"Max Daily Turnover: ₹{args.max_daily_turnover:,.2f}")
    print(f"Max Daily Loss    : ₹{args.max_daily_loss:,.2f}")
    print(f"Max Trades Per Day: {args.max_trades}")
    print(f"Market Hours Guard: {'Active (09:15 - 15:30 IST)' if args.enforce_market_hours else 'Disabled'}")
    print("=" * 65)

    # 1. Initialize Broker
    has_credentials = bool(os.getenv("BROKER_API_KEY") or os.getenv("ZERODHA_API_KEY") or os.getenv("ANGEL_API_KEY"))
    broker = init_broker(args.broker, is_mock=(not has_credentials))

    auth_success = broker.authenticate()
    if not auth_success and not broker.is_mock:
        print(f"\n[ERROR] Failed to authenticate with {args.broker.upper()}.")
        print("Please check your API key, secret, and access token in .env.")
        sys.exit(1)

    margins = broker.get_margins()
    print(f"\nBroker Connection: Authenticated (Mode: {'Mock' if broker.is_mock else 'Live'})")
    print(f"Available Cash   : ₹{margins.get('available', 0):,.2f}")

    # 2. Safety Confirmation for Live Orders
    if is_live:
        print("\n" + "!" * 65)
        print("WARNING: You are about to engage LIVE ORDER ROUTING with REAL CAPITAL.")
        print("Real money orders will be submitted to the exchange via your broker.")
        print("!" * 65)
        conf = input("\nType 'I_CONFIRM_LIVE_TRADING' to proceed (or any key to cancel): ").strip()
        if conf != "I_CONFIRM_LIVE_TRADING":
            print("[ABORTED] Live trading was not confirmed. Exiting.")
            sys.exit(0)

    # 3. Initialize Risk Guard & Order Execution Engine
    risk_guard = AdvancedRiskGuard(
        max_daily_loss=args.max_daily_loss,
        max_trades=args.max_trades,
        total_capital=margins.get("available", 50000.0)
    )

    engine = OrderExecutionEngine(
        broker=broker,
        risk_guard=risk_guard,
        max_order_value=args.max_order_value,
        max_daily_turnover=args.max_daily_turnover,
        dry_run=dry_run,
        enforce_market_hours=args.enforce_market_hours
    )

    if is_live:
        engine.disengage_kill_switch("I_CONFIRM_LIVE_TRADING")

    alert_mgr = AlertManager(notifiers=[ConsoleNotifier()])
    dashboard = PaperTradingDashboard()

    # 4. Initialize Feed
    if has_credentials and not broker.is_mock:
        api_key = os.getenv("BROKER_API_KEY", "")
        access_token = os.getenv("BROKER_ACCESS_TOKEN", "")
        feed = LiveBrokerWebSocketFeed(
            broker_name=args.broker,
            api_key=api_key,
            access_token=access_token,
            timeframe_minutes=args.timeframe
        )
    else:
        print("\nNote: Using real-time synthetic feed for tick streaming (Broker credentials not set).")
        feed = SimulatedWebSocketFeed(
            timeframe_minutes=args.timeframe,
            tick_interval_sec=0.5
        )

    # 5. Handle Shutdown
    def handle_signal(sig, frame):
        print("\n[EMERGENCY STOP] Engaging Kill Switch and shutting down...")
        engine.engage_kill_switch(reason="Manual Ctrl+C shutdown")
        feed.disconnect()
        print(f"Total Session Turnover: ₹{engine.daily_turnover:,.2f}")
        print(f"Audit Log Records: {len(engine.audit_log)}")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)

    # 6. Start Live Loop
    feed.subscribe(symbols)
    feed.connect()
    print("\nLive trading engine is active. Monitoring market... (Press Ctrl+C to stop)")

    try:
        while True:
            time.sleep(2.0)
            # Periodic risk and margin check
            current_margins = broker.get_margins()
            if dashboard:
                dash_broker = {
                    "balance": current_margins.get("available", 0),
                    "committed_capital": current_margins.get("used", 0),
                    "realized_pnl": 0.0,
                    "unrealized_pnl": 0.0,
                    "positions": {p["symbol"]: p for p in broker.get_positions()},
                    "total_trades": len(engine.audit_log),
                    "blocked_entries": sum(1 for e in engine.audit_log if not e["passed_safety"])
                }
                dashboard.render(dash_broker, risk_guard.get_report())
    except KeyboardInterrupt:
        handle_signal(None, None)


if __name__ == "__main__":
    main()
