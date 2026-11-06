
from src.market_data.data_loader import load_market_data
from src.analysis.indicators import calculate_all_indicators
from src.backtesting.backtester import run_backtest

df = load_market_data("data/sample_nse_5m.csv")

results = []

for symbol, stock_data in df.groupby("symbol"):

    analyzed = calculate_all_indicators(stock_data)

    report = run_backtest(
        analyzed,
        initial_capital=10000,
        risk_per_trade=100
    )

    results.append({
        "symbol": symbol,
        **{key: value for key, value in report.items()
           if key != "trade_history"}
    })
    report = run_backtest(
    analyzed,
    initial_capital=10000,
    risk_per_trade=100,
    brokerage_per_order=5,
    charges_rate=0.001,
    slippage_per_share=0.50
)

print("\nINDIAN DAY TRADER - BACKTEST REPORT")
print("=" * 60)

import pandas as pd

print(pd.DataFrame(results).to_string(index=False))
