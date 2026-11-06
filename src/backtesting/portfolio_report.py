
import pandas as pd


def calculate_trade_metrics(trades):

    if not trades:
        return {
            "average_win": 0,
            "average_loss": 0,
            "risk_reward_ratio": None,
            "expectancy": 0,
            "net_profit_factor": None,
            "breakeven_trades": 0
        }

    net_values = [
        float(trade.get("net_pnl", 0))
        for trade in trades
    ]

    winning_trades = [
        value for value in net_values if value > 0
    ]

    losing_trades = [
        value for value in net_values if value < 0
    ]

    breakeven_trades = sum(
        value == 0 for value in net_values
    )

    average_win = (
        sum(winning_trades) / len(winning_trades)
        if winning_trades else 0
    )

    average_loss = (
        abs(sum(losing_trades) / len(losing_trades))
        if losing_trades else 0
    )

    risk_reward_ratio = (
        average_win / average_loss
        if average_loss > 0 else None
    )

    net_profit_factor = (
        sum(winning_trades) / abs(sum(losing_trades))
        if losing_trades else None
    )

    expectancy = (
        sum(net_values) / len(net_values)
    )

    return {
        "average_win": round(average_win, 2),
        "average_loss": round(average_loss, 2),

        "risk_reward_ratio": (
            round(risk_reward_ratio, 2)
            if risk_reward_ratio is not None else None
        ),

        "expectancy": round(expectancy, 2),

        "net_profit_factor": (
            round(net_profit_factor, 2)
            if net_profit_factor is not None else None
        ),

        "breakeven_trades": breakeven_trades
    }


def build_portfolio_summary(report):

    trades = report.get("trade_history", [])

    metrics = calculate_trade_metrics(trades)

    gross_profit = sum(
        max(0, float(trade.get("gross_pnl", 0)))
        for trade in trades
    )

    gross_loss = abs(sum(
        min(0, float(trade.get("gross_pnl", 0)))
        for trade in trades
    ))

    total_costs = report.get("total_costs", 0)

    cost_percentage = (
        total_costs / gross_profit * 100
        if gross_profit > 0 else 0
    )

    summary = {
        "initial_capital": report["initial_capital"],
        "final_capital": report["final_capital"],
        "net_pnl": report["net_pnl"],
        "return_percent": report.get("return_percent", 0),

        "total_costs": total_costs,
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),

        "cost_percentage_of_gross_profit": round(
            cost_percentage, 2
        ),

        "total_trades": report["total_trades"],
        "winning_trades": report["winning_trades"],
        "losing_trades": report["losing_trades"],

        "win_rate": report["win_rate"],
        "profit_factor": report["profit_factor"],

        "max_drawdown_amount": report.get(
            "max_drawdown_amount", 0
        ),

        "max_drawdown_percent": report.get(
            "max_drawdown_percent", 0
        ),

        "recovery_factor": report.get(
            "recovery_factor"
        ),

        "blocked_entries": report.get(
            "blocked_entries", 0
        ),

        **metrics
    }

    return summary


def get_symbol_performance(report):

    trades = report.get("trade_history", [])

    columns = [
        "symbol",
        "trades",
        "winning_trades",
        "losing_trades",
        "breakeven_trades",
        "net_pnl",
        "total_costs",
        "average_net_pnl",
        "win_rate"
    ]

    if not trades:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(trades)

    result = df.groupby("symbol").agg(
        trades=("net_pnl", "count"),

        winning_trades=(
            "net_pnl",
            lambda x: (x > 0).sum()
        ),

        losing_trades=(
            "net_pnl",
            lambda x: (x < 0).sum()
        ),

        breakeven_trades=(
            "net_pnl",
            lambda x: (x == 0).sum()
        ),

        net_pnl=("net_pnl", "sum"),

        total_costs=("total_cost", "sum"),

        average_net_pnl=("net_pnl", "mean")

    ).reset_index()

    result["win_rate"] = (
        result["winning_trades"]
        / result["trades"] * 100
    )

    numeric_columns = [
        "net_pnl",
        "total_costs",
        "average_net_pnl",
        "win_rate"
    ]

    result[numeric_columns] = (
        result[numeric_columns].round(2)
    )

    return result.sort_values(
        "net_pnl",
        ascending=False
    ).reset_index(drop=True)


def get_daily_performance(report):

    history = report.get("equity_history", [])

    columns = [
        "date",
        "closing_equity",
        "daily_pnl",
        "max_drawdown_percent"
    ]

    if not history:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(history)

    if "timestamp" not in df.columns:
        return pd.DataFrame(columns=columns)

    df = df.dropna(subset=["timestamp"]).copy()

    if df.empty:
        return pd.DataFrame(columns=columns)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"]
    )

    df = df.sort_values("timestamp")

    df["date"] = df["timestamp"].dt.date

    daily_rows = []

    previous_equity = report["initial_capital"]

    running_peak = report["initial_capital"]

    for day, group in df.groupby("date", sort=True):

        closing_equity = float(
            group.iloc[-1]["equity"]
        )

        day_drawdowns = []

        for equity_value in group["equity"]:

            equity_value = float(equity_value)

            running_peak = max(
                running_peak,
                equity_value
            )

            drawdown = (
                (running_peak - equity_value)
                / running_peak * 100
                if running_peak > 0 else 0
            )

            day_drawdowns.append(drawdown)

        daily_pnl = (
            closing_equity - previous_equity
        )

        daily_rows.append({
            "date": str(day),

            "closing_equity": round(
                closing_equity, 2
            ),

            "daily_pnl": round(
                daily_pnl, 2
            ),

            "max_drawdown_percent": round(
                max(day_drawdowns, default=0), 2
            )
        })

        previous_equity = closing_equity

    return pd.DataFrame(
        daily_rows,
        columns=columns
    )


def get_trade_history(report):

    trades = report.get("trade_history", [])

    columns = [
        "symbol",
        "entry_time",
        "exit_time",
        "entry",
        "exit",
        "quantity",
        "reason",
        "gross_pnl",
        "total_cost",
        "net_pnl"
    ]

    if not trades:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(trades)

    return df.reindex(
        columns=columns
    ).copy()



def build_portfolio_summary(report):

    trades = report.get("trade_history", [])

    advanced_metrics = calculate_trade_metrics(trades)

    initial_capital = report.get("initial_capital", 0)
    final_capital = report.get("final_capital", initial_capital)

    gross_profit = sum(
        max(float(trade.get("gross_pnl", 0)), 0)
        for trade in trades
    )

    gross_loss = abs(sum(
        min(float(trade.get("gross_pnl", 0)), 0)
        for trade in trades
    ))

    total_costs = report.get("total_costs", 0)

    cost_percentage = (
        (total_costs / gross_profit) * 100
        if gross_profit > 0 else 0
    )

    summary = {
        "initial_capital": initial_capital,
        "final_capital": final_capital,
        "net_pnl": report.get("net_pnl", final_capital - initial_capital),
        "total_trades": report.get("total_trades", len(trades)),
        "winning_trades": report.get("winning_trades", 0),
        "losing_trades": report.get("losing_trades", 0),
        "win_rate": report.get("win_rate", 0),
        "profit_factor": report.get("profit_factor", 0),
        "max_drawdown_percent": report.get("max_drawdown_percent", 0),
        "max_drawdown_amount": report.get("max_drawdown_amount", 0),
        "return_percent": report.get(
            "return_percent",
            ((final_capital - initial_capital) / initial_capital * 100)
            if initial_capital else 0
        ),
        "recovery_factor": report.get("recovery_factor", 0),
        "blocked_entries": report.get("blocked_entries", 0),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "total_costs": total_costs,
        "cost_percentage_of_gross_profit": cost_percentage
    }

    summary.update(advanced_metrics)

    return summary


def print_portfolio_dashboard(report):
    """
    Print a complete formatted portfolio dashboard to the console.
    """
    summary = build_portfolio_summary(report)
    print("\n" + "=" * 65)
    print("             PORTFOLIO BACKTEST DASHBOARD")
    print("=" * 65)
    print(f"Initial Capital   : Rs. {summary.get('initial_capital', 0):,.2f}")
    print(f"Final Capital     : Rs. {summary.get('final_capital', 0):,.2f}")
    print(f"Net P&L           : Rs. {summary.get('net_pnl', 0):,.2f} ({summary.get('return_percent', 0):.2f}%)")
    print(f"Total Trades      : {summary.get('total_trades', 0)} (Wins: {summary.get('winning_trades', 0)}, Losses: {summary.get('losing_trades', 0)})")
    print(f"Win Rate          : {summary.get('win_rate', 0):.2f}%")
    print(f"Profit Factor     : {summary.get('profit_factor', 0):.2f}")
    print(f"Max Drawdown      : {summary.get('max_drawdown_percent', 0):.2f}% (Rs. {summary.get('max_drawdown_amount', 0):,.2f})")
    print(f"Total Costs       : Rs. {summary.get('total_costs', 0):,.2f}")
    print(f"Blocked Entries   : {summary.get('blocked_entries', 0)}")

    symbols_df = get_symbol_performance(report)
    if not symbols_df.empty:
        print("\n--- SYMBOL PERFORMANCE ---")
        print(symbols_df.to_string(index=False))

    daily_df = get_daily_performance(report)
    if not daily_df.empty:
        print("\n--- DAILY PERFORMANCE ---")
        print(daily_df.to_string(index=False))

    print("=" * 65 + "\n")
    return summary
