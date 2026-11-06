import pandas as pd

from src.risk.trading_costs import (
    calculate_trading_costs,
    calculate_indian_equity_intraday_costs
)
from src.risk.portfolio_risk_guard import PortfolioRiskGuard

from src.backtesting.execution import check_exit_conditions

from src.utils.market_session import (
    is_market_session,
    is_entry_allowed,
    is_square_off_time
)

def run_portfolio_backtest(
    df,
    initial_capital=10000,
    risk_per_trade=100,
    brokerage_per_order=5,
    charges_rate=0.001,
    slippage_per_share=0.50,
    max_daily_loss=500,
    max_trades_per_day=3,
    cost_settings=None,
    fast_ema_period=9,
    slow_ema_period=21,
    stop_loss_pct=0.01,
    target_pct=0.02
):
    """
    Run a shared-capital portfolio backtest.

    If cost_settings is supplied, Indian equity intraday costs are used.
    Otherwise, the legacy calculate_trading_costs function is used.

    This is a backtesting simulation. It does not place live orders.
    """

    # ---------------------------------------------------------
    # 1. Validate input
    # ---------------------------------------------------------

    if (
    not isinstance(fast_ema_period, int)
    or isinstance(fast_ema_period, bool)
    or not isinstance(slow_ema_period, int)
    or isinstance(slow_ema_period, bool)
    or fast_ema_period <= 0
    or slow_ema_period <= 0
    or fast_ema_period >= slow_ema_period
    ):
        raise ValueError("Invalid EMA strategy periods.")

    if (
        stop_loss_pct <= 0
        or target_pct <= 0
        or stop_loss_pct >= 1
    ):
        raise ValueError("Invalid stop-loss or target percentage.")

    fast_column = f"EMA_{fast_ema_period}"
    slow_column = f"EMA_{slow_ema_period}"

    required = [
        "timestamp",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        fast_column,
        slow_column
    ]

    missing = [
        column for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    if initial_capital <= 0 or risk_per_trade <= 0:
        raise ValueError("Capital and risk must be positive.")

    if max_daily_loss <= 0 or max_trades_per_day <= 0:
        raise ValueError("Daily risk limits must be positive.")

    if (
        not isinstance(fast_ema_period, int)
        or not isinstance(slow_ema_period, int)
        or fast_ema_period <= 0
        or slow_ema_period <= 0
        or fast_ema_period >= slow_ema_period
    ):
        raise ValueError("Invalid EMA strategy periods.")

    if (
        stop_loss_pct <= 0
        or target_pct <= 0
        or stop_loss_pct >= 1
    ):
        raise ValueError("Invalid stop-loss or target percentage.")
    
    if min(
        brokerage_per_order,
        charges_rate,
        slippage_per_share
    ) < 0:
        raise ValueError("Trading costs cannot be negative.")

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    if df["timestamp"].isna().any():
        raise ValueError("Invalid timestamps found.")

    if (
        df["symbol"].isna().any()
        or (
            df["symbol"].astype(str).str.strip() == ""
        ).any()
    ):
        raise ValueError("Invalid symbols found.")

    df["symbol"] = df["symbol"].astype(str).str.strip()

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        fast_column,
        slow_column
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    if df[numeric_columns].isna().any().any():
        raise ValueError("Invalid price or indicator values.")

    # Keep only candles inside the configured market session.
    df = df[
        df["timestamp"].apply(is_market_session)
    ].copy()

    if df.empty:
        raise ValueError("No candles inside the market session.")

    if (
        df[["open", "high", "low", "close"]] <= 0
    ).any().any():
        raise ValueError("Prices must be positive.")

    invalid_ohlc = (
        df["high"] < df[["open", "close", "low"]].max(axis=1)
    ) | (
        df["low"] > df[["open", "close", "high"]].min(axis=1)
    )

    if invalid_ohlc.any():
        raise ValueError("Invalid OHLC candle data.")

    if df.duplicated(["timestamp", "symbol"]).any():
        raise ValueError(
            "Duplicate timestamp and symbol combinations found."
        )

    df = df.sort_values(
        ["timestamp", "symbol"]
    ).reset_index(drop=True)
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("No market data available.")

    # Work on a copy so backtesting never changes the caller's data.
    df = df.copy()
    # ---------------------------------------------------------
    # 2. Prepare Indian transaction-cost settings
    # ---------------------------------------------------------

    # Accept either the complete settings.json dictionary
    # or only its "costs" section.
    if cost_settings is not None:
        if "costs" in cost_settings:
            cost_settings = cost_settings["costs"]

        brokerage_config = cost_settings.get(
            "brokerage", {}
        )

        indian_cost_parameters = {
            "brokerage_rate": brokerage_config.get(
                "rate", 0.001
            ),
            "brokerage_cap": brokerage_config.get(
                "maximum_per_order", 20
            ),
            "brokerage_minimum": brokerage_config.get(
                "minimum_per_order", 5
            ),
            "brokerage_minimum_rate": brokerage_config.get(
                "minimum_rate", 0.025
            ),
            "stt_sell_rate": cost_settings.get(
                "stt_sell_rate", 0.00025
            ),
            "stamp_duty_buy_rate": cost_settings.get(
                "stamp_duty_buy_rate", 0.00003
            ),
            "exchange_transaction_rate": cost_settings.get(
                "exchange_transaction_rate"
            ),
            "sebi_turnover_rate": cost_settings.get(
                "sebi_turnover_rate", 0.000001
            ),
            "ipft_rate": cost_settings.get("ipft_rate"),
            "gst_rate": cost_settings.get(
                "gst_rate", 0.18
            ),
            "slippage_per_share": cost_settings.get(
                "slippage_per_share", 0.05
            )
        }
    else:
        indian_cost_parameters = None

    # ---------------------------------------------------------
    # 3. Portfolio state
    # ---------------------------------------------------------

    balance = float(initial_capital)

    positions = {}
    previous_candles = {}
    last_prices = {}

    trades = []
    blocked_entries = 0

    equity_curve = [balance]

    equity_history = [
        {
            "timestamp": None,
            "equity": balance,
            "balance": balance,
            "unrealized_pnl": 0.0
        }
    ]

    daily_reports = []

    risk_guard = PortfolioRiskGuard(
        max_daily_loss=max_daily_loss,
        max_trades=max_trades_per_day
    )

    active_day = None
    previous_timestamp = None

    # ---------------------------------------------------------
    # 4. Cost calculation helpers
    # ---------------------------------------------------------

    def calculate_position_costs(
        position,
        exit_price
    ):
        """
        Calculate estimated round-trip costs and P&L
        for an existing position.
        """

        if indian_cost_parameters is not None:
            return calculate_indian_equity_intraday_costs(
                entry_price=position["entry"],
                exit_price=exit_price,
                quantity=position["quantity"],
                exchange=position.get("exchange", "NSE"),
                **indian_cost_parameters
            )

        return calculate_trading_costs(
            entry_price=position["entry"],
            exit_price=exit_price,
            quantity=position["quantity"],
            brokerage_per_order=brokerage_per_order,
            charges_rate=charges_rate,
            slippage_per_share=slippage_per_share
        )

    def calculate_position_unrealized(
        position,
        current_price
    ):
        """
        Estimate net unrealized P&L after estimated
        round-trip costs.
        """

        costs = calculate_position_costs(
            position,
            current_price
        )

        return costs["net_pnl"]

    def portfolio_unrealized():
        total = 0.0

        for symbol, position in positions.items():
            current_price = last_prices.get(
                symbol,
                position["entry"]
            )

            total += calculate_position_unrealized(
                position,
                current_price
            )

        return total

    # ---------------------------------------------------------
    # 5. Position closing helpers
    # ---------------------------------------------------------

    def close_position(
        symbol,
        exit_price,
        timestamp,
        reason
    ):
        nonlocal balance

        if symbol not in positions:
            return

        position = positions[symbol]

        costs = calculate_position_costs(
            position,
            exit_price
        )

        net_pnl = costs["net_pnl"]

        balance += net_pnl

        risk_guard.record_trade(net_pnl)

        trade_record = {
            "symbol": symbol,
            "exchange": position.get("exchange", "NSE"),
            "entry_time": position["entry_time"],
            "exit_time": timestamp,
            "entry": position["entry"],
            "exit": exit_price,
            "quantity": position["quantity"],
            "reason": reason,
            **costs
        }

        trades.append(trade_record)

        del positions[symbol]

    def close_all_positions(timestamp, reason):
        for symbol in list(positions.keys()):
            exit_price = last_prices.get(
                symbol,
                positions[symbol]["entry"]
            )

            close_position(
                symbol=symbol,
                exit_price=exit_price,
                timestamp=timestamp,
                reason=reason
            )

    # ---------------------------------------------------------
    # 6. Main portfolio simulation
    # ---------------------------------------------------------

    for timestamp, group in df.groupby(
        "timestamp",
        sort=True
    ):

        current_day = timestamp.date()

        # -----------------------------------------------------
        # Handle a new trading day
        # -----------------------------------------------------

        if (
            active_day is not None
            and current_day != active_day
        ):

            had_positions = bool(positions)

            if had_positions:
                close_all_positions(
                    previous_timestamp,
                    "END_OF_SESSION"
                )

                equity_curve.append(balance)

                equity_history.append({
                    "timestamp": previous_timestamp,
                    "equity": balance,
                    "balance": balance,
                    "unrealized_pnl": 0.0
                })

            daily_reports.append({
                "date": str(active_day),
                **risk_guard.get_report()
            })

            risk_guard.reset()

        active_day = current_day

        candles = {
            row["symbol"]: row
            for _, row in group.iterrows()
        }

        closed_symbols = set()

        # -----------------------------------------------------
        # Update latest market prices
        # -----------------------------------------------------

        for symbol, candle in candles.items():
            last_prices[symbol] = candle["close"]

        # -----------------------------------------------------
        # Monitor existing positions first
        # -----------------------------------------------------

        for symbol in list(positions.keys()):

            if symbol not in candles:
                continue

            candle = candles[symbol]

            positions[symbol]["last_checked_time"] = timestamp

            # Time-based square-off
            if is_square_off_time(timestamp):

                close_position(
                    symbol,
                    candle["close"],
                    timestamp,
                    "TIME_BASED_SQUARE_OFF"
                )

                closed_symbols.add(symbol)
                continue

            # Stop-loss and target checks
            exit_result = check_exit_conditions(
                candle,
                positions[symbol]
            )

            if exit_result is not None:

                exit_price, reason = exit_result

                close_position(
                    symbol,
                    exit_price,
                    timestamp,
                    reason
                )

                closed_symbols.add(symbol)

        # -----------------------------------------------------
        # Calculate combined unrealized P&L
        # -----------------------------------------------------

        unrealized = portfolio_unrealized()

        # -----------------------------------------------------
        # Daily loss protection
        # -----------------------------------------------------

        if (
            positions
            and risk_guard.daily_loss(unrealized) >= max_daily_loss
        ):

            close_all_positions(
                timestamp,
                "DAILY_LOSS_SQUARE_OFF"
            )

            closed_symbols.update(candles.keys())

        # -----------------------------------------------------
        # Find new entry opportunities
        # -----------------------------------------------------

        for symbol in sorted(candles.keys()):

            candle = candles[symbol]

            if (
                symbol in positions
                or symbol in closed_symbols
            ):
                continue

            previous = previous_candles.get(symbol)

            if previous is None:
                continue

            valid_crossover = (
                previous["timestamp"].date() == current_day
                and previous[fast_column] <= previous[slow_column]
                and candle[fast_column] > candle[slow_column]
            )

            if not valid_crossover:
                continue

            # Market entry time restrictions
            if not is_entry_allowed(timestamp):
                blocked_entries += 1
                continue

            unrealized = portfolio_unrealized()

            allowed, message = risk_guard.can_take_trade(
                unrealized
            )

            if not allowed:
                blocked_entries += 1
                continue

            # -------------------------------------------------
            # Shared capital calculation
            # -------------------------------------------------

            committed_capital = sum(
                position["entry"] * position["quantity"]
                for position in positions.values()
            )

            available_capital = max(
                0,
                balance - committed_capital
            )

            entry = float(candle["close"])

            # Strategy stop-loss and target - use parameters
            stop = entry * (1 - stop_loss_pct)
            target = entry * (1 + target_pct)

            risk_per_share_value = entry - stop

            if risk_per_share_value <= 0:
                blocked_entries += 1
                continue

            risk_quantity = int(
                risk_per_trade // risk_per_share_value
            )

            capital_quantity = int(
                available_capital // entry
            )

            quantity = min(
                risk_quantity,
                capital_quantity
            )

            if quantity <= 0:
                blocked_entries += 1
                continue

            exchange = str(
                candle.get("exchange", "NSE")
            ).upper()

            if exchange not in ("NSE", "BSE"):
                blocked_entries += 1
                continue

            positions[symbol] = {
                "entry": entry,
                "stop": stop,
                "target": target,
                "quantity": quantity,
                "entry_time": timestamp,
                "last_checked_time": timestamp,
                "exchange": exchange
            }

            risk_guard.record_entry()

        # -----------------------------------------------------
        # Mark-to-market portfolio equity
        # -----------------------------------------------------

        current_unrealized = portfolio_unrealized()

        current_equity = balance + current_unrealized

        equity_curve.append(current_equity)

        equity_history.append({
            "timestamp": timestamp,
            "equity": current_equity,
            "balance": balance,
            "unrealized_pnl": current_unrealized
        })

        # Save candles for the next crossover check
        for symbol, candle in candles.items():
            previous_candles[symbol] = candle

        previous_timestamp = timestamp

    # ---------------------------------------------------------
    # 7. Close positions at end of available data
    # ---------------------------------------------------------

    if positions:

        close_all_positions(
            previous_timestamp,
            "END_OF_DATA"
        )

        # Record final realized equity after closing positions.
        equity_curve.append(balance)

        equity_history.append({
            "timestamp": previous_timestamp,
            "equity": balance,
            "balance": balance,
            "unrealized_pnl": 0.0
        })

    # Save the final day's risk report
    if active_day is not None:
        daily_reports.append({
            "date": str(active_day),
            **risk_guard.get_report()
        })

    # ---------------------------------------------------------
    # 8. Calculate performance metrics
    # ---------------------------------------------------------

    total_trades = len(trades)

    wins = [
        trade for trade in trades
        if trade["net_pnl"] > 0
    ]

    losses = [
        trade for trade in trades
        if trade["net_pnl"] < 0
    ]

    breakeven_trades = [
        trade for trade in trades
        if trade["net_pnl"] == 0
    ]

    net_pnl = sum(
        trade["net_pnl"]
        for trade in trades
    )

    total_costs = sum(
        trade["total_cost"]
        for trade in trades
    )

    gross_profit = sum(
        max(0, trade["gross_pnl"])
        for trade in trades
    )

    gross_loss = abs(sum(
        min(0, trade["gross_pnl"])
        for trade in trades
    ))

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
        if losing_net > 0
        else None
    )

    win_rate = (
        len(wins) / total_trades * 100
        if total_trades > 0
        else 0
    )

    # ---------------------------------------------------------
    # 9. Equity and drawdown metrics
    # ---------------------------------------------------------

    equity = pd.Series(
        equity_curve,
        dtype="float64"
    )

    peak = equity.cummax()

    drawdown_amount = peak - equity

    drawdown_percent = (
        drawdown_amount / peak.replace(0, pd.NA)
    ) * 100

    max_drawdown_amount = float(
        drawdown_amount.max()
    )

    max_drawdown_percent = float(
        drawdown_percent.fillna(0).max()
    )

    return_percent = (
        net_pnl / initial_capital
    ) * 100

    recovery_factor = (
        net_pnl / max_drawdown_amount
        if max_drawdown_amount > 0
        else None
    )

    # ---------------------------------------------------------
    # 10. Final report
    # ---------------------------------------------------------

    return {
        "initial_capital": round(initial_capital, 2),
        "final_capital": round(balance, 2),
        "net_pnl": round(net_pnl, 2),
        "total_costs": round(total_costs, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),

        "total_trades": total_trades,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "breakeven_trades": len(breakeven_trades),

        "win_rate": round(win_rate, 2),

        "profit_factor": (
            round(profit_factor, 2)
            if profit_factor is not None
            else None
        ),

        "max_drawdown_amount": round(
            max_drawdown_amount,
            2
        ),

        "max_drawdown_percent": round(
            max_drawdown_percent,
            2
        ),

        "return_percent": round(
            return_percent,
            2
        ),

        "recovery_factor": (
            round(recovery_factor, 2)
            if recovery_factor is not None
            else None
        ),

        "blocked_entries": blocked_entries,
        "remaining_positions": len(positions),

        "daily_risk_reports": daily_reports,
        "trade_history": trades,
        "equity_curve": equity_curve,
        "equity_history": equity_history
    }