
from src.risk.daily_risk_guard import DailyRiskGuard
from src.paper_trading.paper_broker import PaperBroker


guard = DailyRiskGuard(max_daily_loss=500, max_trades=3)
broker = PaperBroker(guard)

print("\nAUTOMATIC EXIT TEST")
print("=" * 45)

# Open a simulated position
print("\nOPEN POSITION:")

print(broker.buy(
    symbol="RELIANCE",
    entry=1000,
    stop_loss=990,
    target=1020,
    capital=10000,
    risk_per_trade=100
))

# Simulate a candle that reaches the target
print("\nMONITOR CANDLE:")

result = broker.monitor_candle(
    high=1005,
    low=985
)

print(result)

print("\nDAILY REPORT:")
print(guard.get_report())
