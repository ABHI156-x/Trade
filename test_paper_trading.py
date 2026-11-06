
from src.risk.daily_risk_guard import DailyRiskGuard
from src.paper_trading.paper_broker import PaperBroker


guard = DailyRiskGuard(
    max_daily_loss=500,
    max_trades=3
)

broker = PaperBroker(guard)

print("\nINDIAN DAY TRADER - PAPER TRADING")
print("=" * 45)

# Open a simulated position
result = broker.buy(
    symbol="RELIANCE",
    entry=1000,
    stop_loss=990,
    target=1020,
    capital=10000,
    risk_per_trade=100
)

print("\nBUY RESULT:")
print(result)

# Simulate selling at ₹1020
result = broker.sell(exit_price=1020)

print("\nSELL RESULT:")
print(result)

# Show daily report
print("\nDAILY RISK REPORT:")
print(guard.get_report())
