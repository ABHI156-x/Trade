
from src.risk.trading_costs import calculate_trading_costs

result = calculate_trading_costs(
    entry_price=1000,
    exit_price=1020,
    quantity=10,
    brokerage_per_order=5,
    charges_rate=0.001,
    slippage_per_share=0.50
)

print("\nTRADING COST REPORT")
print("=" * 40)

for key, value in result.items():
    print(f"{key}: {value}")
