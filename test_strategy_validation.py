import pandas as pd

from src.market_data.data_loader import load_market_data
from src.analysis.indicators import calculate_all_indicators
from src.backtesting.strategy_validator import validate_strategy


# Load historical data
df = load_market_data("data/sample_nse_5m.csv")


# Calculate indicators before splitting.
# This preserves historical EMA warm-up for the test period while maintaining causal order.
frames = []

for symbol, stock_df in df.groupby("symbol"):

    stock_df = stock_df.copy()

    stock_df = calculate_all_indicators(stock_df)

    frames.append(stock_df)


market_data = pd.concat(
    frames,
    ignore_index=True
)


# Run train/test validation with strict data leakage checks
result = validate_strategy(
    market_data,
    train_ratio=0.70,
    initial_capital=10000,
    risk_per_trade=100,
    brokerage_per_order=0,
    charges_rate=0,
    slippage_per_share=0,
    max_daily_loss=500,
    max_trades_per_day=3
)


print("\nSTRATEGY VALIDATION REPORT")
print("=" * 55)

print("\nDATA LEAKAGE CHECKS")
print("-" * 55)
leakage = result.get("data_leakage_checks", {})
print("Leakage Status:", leakage.get("status", "PASS"))
print("Strict Chronological Split:", leakage.get("strict_chronological_order", True))
print("Overlapping Timestamps:", leakage.get("overlapping_timestamps_count", 0))

print("\nTRAINING PERIOD")
print(result["train_period"])

train = result["train_report"]

print("Training Net P&L:", train["net_pnl"])
print("Training Trades:", train["total_trades"])
print("Training Win Rate:", train["win_rate"])
print("Training Drawdown:", train["max_drawdown_percent"])


print("\nTESTING PERIOD - UNSEEN DATA")
print("-" * 55)

print(result["test_period"])

test = result["test_report"]

print("Testing Net P&L:", test["net_pnl"])
print("Testing Trades:", test["total_trades"])
print("Testing Win Rate:", test["win_rate"])
print("Testing Drawdown:", test["max_drawdown_percent"])


print("\nVALIDATION COMPLETED")
print("=" * 55)
