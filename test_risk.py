
from src.risk.risk_manager import calculate_position_size

result = calculate_position_size(
    entry_price=1000,
    stop_loss=990,
    target_price=1020,
    available_capital=10000,
    risk_per_trade=100,
    daily_loss=500,
    max_daily_loss=500
)

print("\nINDIAN DAY TRADER - RISK REPORT")
print("=" * 45)

for key, value in result.items():
    print(f"{key}: {value}")
