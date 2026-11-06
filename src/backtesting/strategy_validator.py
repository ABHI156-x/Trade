
from src.backtesting.data_splitter import split_market_data
from src.backtesting.portfolio_backtester import run_portfolio_backtest


def validate_strategy(
    df,
    train_ratio=0.70,
    initial_capital=10000,
    risk_per_trade=100,
    brokerage_per_order=0,
    charges_rate=0,
    slippage_per_share=0,
    max_daily_loss=500,
    max_trades_per_day=3
):

    required_columns = [
        "timestamp",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "EMA_9",
        "EMA_21"
    ]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(f"Missing column: {column}")

    train_data, test_data = split_market_data(
        df,
        train_ratio
    )

    settings = {
        "initial_capital": initial_capital,
        "risk_per_trade": risk_per_trade,
        "brokerage_per_order": brokerage_per_order,
        "charges_rate": charges_rate,
        "slippage_per_share": slippage_per_share,
        "max_daily_loss": max_daily_loss,
        "max_trades_per_day": max_trades_per_day
    }

    train_report = run_portfolio_backtest(
        train_data,
        **settings
    )

    test_report = run_portfolio_backtest(
        test_data,
        **settings
    )

    return {
        "train_period": {
            "start": str(train_data["timestamp"].min()),
            "end": str(train_data["timestamp"].max()),
            "candles": len(train_data)
        },
        "test_period": {
            "start": str(test_data["timestamp"].min()),
            "end": str(test_data["timestamp"].max()),
            "candles": len(test_data)
        },
        "train_report": train_report,
        "test_report": test_report
    }
