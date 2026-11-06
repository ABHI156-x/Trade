
from src.market_data.data_loader import load_market_data
from src.analysis.indicators import calculate_all_indicators
from src.backtesting.portfolio_backtester import run_portfolio_backtest
from src.backtesting.portfolio_report import print_portfolio_dashboard


# 1. Load sample market data
df = load_market_data("data/sample_nse_5m.csv")


# 2. Calculate indicators separately for each stock
frames = []

for symbol, stock_df in df.groupby("symbol"):

    stock_df = stock_df.copy()

    stock_df = calculate_all_indicators(stock_df)

    frames.append(stock_df)


# 3. Combine all stocks
import pandas as pd

market_data = pd.concat(
    frames,
    ignore_index=True
)


# 4. Run portfolio backtest
report = run_portfolio_backtest(
    market_data,
    initial_capital=10000,
    risk_per_trade=100,
    brokerage_per_order=0,
    charges_rate=0,
    slippage_per_share=0,
    max_daily_loss=500,
    max_trades_per_day=3
)


# 5. Display portfolio dashboard
print_portfolio_dashboard(report)
