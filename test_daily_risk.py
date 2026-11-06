
from src.risk.daily_risk_guard import DailyRiskGuard

guard = DailyRiskGuard(
    max_daily_loss=500,
    max_trades=3
)

print("\nINDIAN DAY TRADER - DAILY RISK GUARD")
print("=" * 45)

# Trade 1: Loss of ₹100
print("\nTrade 1:")
print(guard.register_trade(-100))

# Trade 2: Profit of ₹200
print("\nTrade 2:")
print(guard.register_trade(200))

# Trade 3: Loss of ₹450
print("\nTrade 3:")
print(guard.register_trade(-450))

# Try taking another trade
print("\nTrade 4:")
print(guard.can_take_trade())

# Daily report
print("\nDAILY RISK REPORT")
print("-" * 45)

for key, value in guard.get_report().items():
    print(f"{key}: {value}")
