
import pandas as pd

from src.risk.trading_costs import calculate_trading_costs
from src.risk.daily_risk_guard import DailyRiskGuard
from src.risk.daily_loss_monitor import calculate_unrealized_pnl

from src.backtesting.execution import check_exit_conditions

from src.utils.market_session import (
    is_market_session,
    is_entry_allowed,
    is_square_off_time
)


def run_backtest(
    df,
    initial_capital=10000,
    risk_per_trade=100,
    brokerage_per_order=5,
    charges_rate=0.001,
    slippage_per_share=0.50,
    max_daily_loss=500,
    max_trades_per_day=3
):

    df = df.copy()

    required = [
        "timestamp", "open", "high", "low", "close",
        "EMA_9", "EMA_21"
    ]

    if df.empty:
        raise ValueError("No market data available.")

    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    if df["timestamp"].isna().any():
        raise ValueError("Invalid timestamps found.")

    if df[required[1:]].isna().any().any():
        raise ValueError("Missing price or indicator values.")

    if initial_capital <= 0 or risk_per_trade <= 0:
        raise ValueError("Capital and risk must be positive.")

    if max_daily_loss <= 0 or max_trades_per_day <= 0:
        raise ValueError("Daily risk limits must be positive.")

    # Keep only regular NSE/BSE equity-session candles
    df = df[
        df["timestamp"].apply(is_market_session)
    ].copy()

    df = df.sort_values("timestamp").reset_index(drop=True)

    if df.empty:
        raise ValueError("No candles inside the market session.")

    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Prices must be positive.")

    if (
        (df["high"] < df[["open", "close", "low"]].max(axis=1))
        | (df["low"] > df[["open", "close"]].min(axis=1))
    ).any():
        raise ValueError("Invalid OHLC candle data.")

    balance = initial_capital

    equity_curve = [balance]
    trades = []

    position = None

    risk_guard = DailyRiskGuard(
        max_daily_loss=max_daily_loss,
        max_trades=max_trades_per_day
    )

    blocked_entries = 0

    def close_position(exit_price, reason):

        nonlocal balance, position

        trade = position

        costs = calculate_trading_costs(
            entry_price=trade["entry"],
            exit_price=exit_price,
            quantity=trade["quantity"],
            brokerage_per_order=brokerage_per_order,
            charges_rate=charges_rate,
            slippage_per_share=slippage_per_share
        )

        net_pnl = costs["net_pnl"]

        balance += net_pnl

        # Always record completed trades
        risk_guard.record_trade(net_pnl)

        trades.append({
            "entry_time": trade["entry_time"],
            "exit_time": trade["last_checked_time"],
            "entry": trade["entry"],
            "exit": exit_price,
            "quantity": trade["quantity"],
            "reason": reason,
            **costs
        })

        position = None

    for i in range(1, len(df)):

        previous = df.iloc[i - 1]
        candle = df.iloc[i]

        current_day = candle["timestamp"].date()
        previous_day = previous["timestamp"].date()

        closed_this_candle = False

        # Reset daily risk when a new trading day begins
        if current_day != previous_day:

            if position is not None:

                position["last_checked_time"] = previous["timestamp"]

                close_position(
                    previous["close"],
                    "END_OF_SESSION"
                )

            risk_guard.reset()

        # 1. Monitor existing position
        if position is not None:

            position["last_checked_time"] = candle["timestamp"]

            if is_square_off_time(candle["timestamp"]):

                close_position(
                    candle["close"],
                    "TIME_BASED_SQUARE_OFF"
                )

                closed_this_candle = True

            else:

                exit_result = check_exit_conditions(
                    candle,
                    position
                )

                if exit_result is not None:

                    exit_price, reason = exit_result

                    close_position(
                        exit_price,
                        reason
                    )

                    closed_this_candle = True

        # 2. Automatic daily loss protection
        if position is not None:

            unrealized_pnl = calculate_unrealized_pnl(
                position=position,
                current_price=candle["close"],
                brokerage_per_order=brokerage_per_order,
                charges_rate=charges_rate,
                slippage_per_share=slippage_per_share
            )

            current_daily_loss = risk_guard.daily_loss(
                unrealized_pnl
            )

            if current_daily_loss >= max_daily_loss:

                position["last_checked_time"] = candle["timestamp"]

                close_position(
                    candle["close"],
                    "DAILY_LOSS_SQUARE_OFF"
                )

                closed_this_candle = True

        # 3. Check for a new entry
        if position is None and not closed_this_candle:

            allowed, message = risk_guard.can_take_trade()

            valid_crossover = (
                current_day == previous_day
                and previous["EMA_9"] <= previous["EMA_21"]
                and candle["EMA_9"] > candle["EMA_21"]
            )

            if valid_crossover:

                if not is_entry_allowed(candle["timestamp"]):
                    blocked_entries += 1

                elif not allowed:
                    blocked_entries += 1

                else:

                    entry = candle["close"]

                    stop = entry * 0.99
                    target = entry * 1.02

                    risk_per_share = entry - stop

                    risk_quantity = int(
                        risk_per_trade // risk_per_share
                    )

                    capital_quantity = int(
                        balance // entry
                    )

                    quantity = min(
                        risk_quantity,
                        capital_quantity
                    )

                    if quantity > 0:

                        position = {
                            "entry": entry,
                            "stop": stop,
                            "target": target,
                            "quantity": quantity,
                            "entry_time": candle["timestamp"],
                            "last_checked_time": candle["timestamp"]
                        }

        # 4. Mark-to-market equity
        if position is not None:

            estimated_pnl = calculate_unrealized_pnl(
                position=position,
                current_price=candle["close"],
                brokerage_per_order=brokerage_per_order,
                charges_rate=charges_rate,
                slippage_per_share=slippage_per_share
            )

            current_equity = balance + estimated_pnl

        else:

            current_equity = balance

        equity_curve.append(current_equity)

    # 5. Close any position remaining at the end of available data
    if position is not None:

        position["last_checked_time"] = df.iloc[-1]["timestamp"]

        close_position(
            df.iloc[-1]["close"],
            "END_OF_DATA"
        )

        equity_curve.append(balance)

    # 6. Calculate performance
    total_trades = len(trades)

    wins = [
        trade for trade in trades
        if trade["net_pnl"] > 0
    ]

    losses = [
        trade for trade in trades
        if trade["net_pnl"] < 0
    ]

    gross_profit = sum(
        max(0, trade["gross_pnl"])
        for trade in trades
    )

    gross_loss = abs(sum(
        min(0, trade["gross_pnl"])
        for trade in trades
    ))

    net_profit = sum(
        trade["net_pnl"]
        for trade in trades
    )

    total_costs = sum(
        trade["total_cost"]
        for trade in trades
    )

    win_rate = (
        len(wins) / total_trades * 100
        if total_trades else 0
    )

    winning_net = sum(
        trade["net_pnl"]
        for trade in wins
    )

    losing_net = abs(sum(
        trade["net_pnl"]
        for trade in losses
    ))

    profit_factor = (
        winning_net / losing_net
        if losing_net > 0 else None
    )

    equity = pd.Series(equity_curve)

    peak = equity.cummax()

    drawdown = (
        (peak - equity) / peak
    ) * 100

    max_drawdown = drawdown.max()

    return {
        "initial_capital": initial_capital,
        "final_capital": round(balance, 2),
        "net_pnl": round(net_profit, 2),
        "total_costs": round(total_costs, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "total_trades": total_trades,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(win_rate, 2),
        "profit_factor": (
            round(profit_factor, 2)
            if profit_factor is not None else None
        ),
        "max_drawdown_percent": round(max_drawdown, 2),
        "blocked_entries": blocked_entries,
        "daily_risk_report": risk_guard.get_report(),
        "trade_history": trades
    }
