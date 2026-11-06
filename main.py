
from src.market_data.data_loader import load_market_data
from src.market_data.validators import validate_market_data

from src.scanner.stock_scanner import scan_stocks

from src.analysis.indicators import calculate_indicators_by_symbol

from src.paper_trading.replay_runner import PaperReplayRunner


def main():

    print("\nINDIAN DAY TRADER")
    print("=" * 50)

    # STEP 1: Load market data
    df = load_market_data("data/sample_nse_5m.csv")

    # STEP 2: Validate data
    errors = validate_market_data(df)

    if errors:
        print("\nData validation failed:")

        for error in errors:
            print(error)

        return

    print("\nData validation: PASSED")

    # STEP 3: Stock scanner
    report = scan_stocks(df)

    print("\nSTOCK SCANNER - RANKED REPORT")
    print("-" * 80)

    if report.empty:
        print("No stocks found.")
    else:
        print(report.to_string(index=False))

    # STEP 4: Calculate indicators independently by stock
    market_data = calculate_indicators_by_symbol(df)

    print("\nTechnical indicators calculated.")

    # STEP 5: Automated paper trading
    print("\nAUTOMATED PAPER TRADING")
    print("-" * 80)

    replay = PaperReplayRunner(
        initial_capital=10000,
        risk_per_trade=100,
        max_daily_loss=500,
        max_trades_per_day=3
    )

    trading_report = replay.run(market_data)

    # STEP 6: Display performance
    print("\nPAPER TRADING PERFORMANCE")
    print("-" * 80)

    print("Initial Capital: ₹10,000")
    print(f"Final Capital: ₹{trading_report['final_capital']:.2f}")
    print(f"Total Trades: {trading_report['total_trades']}")
    print(f"Net P&L: ₹{trading_report['net_pnl']:.2f}")

    print("\nCompleted Trades:")

    if trading_report["trade_history"]:
        for trade in trading_report["trade_history"]:
            print(trade)
    else:
        print("No completed trades.")

    print("\nBlocked Entries:")

    print(trading_report["blocked_entries"])

    print("\nTrade journal updated.")
    print("\nTrading simulation completed.")


if __name__ == "__main__":
    main()
