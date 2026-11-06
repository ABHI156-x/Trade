
import math
import pandas as pd


def analyze_regime_performance(backtest_report, regime_data):
    """
    Analyze backtest trade performance by market regime.

    Matches each trade to the regime present at entry.

    Required regime_data columns:
    timestamp, symbol, MARKET_REGIME
    """

    if not isinstance(backtest_report, dict):
        raise ValueError("Invalid backtest report.")

    trades = backtest_report.get("trade_history")

    if not isinstance(trades, list):
        raise ValueError("Missing trade history.")

    if (
        regime_data is None
        or not isinstance(regime_data, pd.DataFrame)
        or regime_data.empty
    ):
        raise ValueError("No market regime data available.")

    required = {"timestamp", "symbol", "MARKET_REGIME"}

    if not required.issubset(regime_data.columns):
        raise ValueError("Missing required regime columns.")

    working_df = regime_data[
        ["timestamp", "symbol", "MARKET_REGIME"]
    ].copy()

    working_df["timestamp"] = pd.to_datetime(
        working_df["timestamp"],
        errors="coerce"
    )

    if working_df["timestamp"].isna().any():
        raise ValueError("Invalid regime timestamps.")

    if working_df["symbol"].isna().any():
        raise ValueError("Invalid regime symbols.")

    if working_df["MARKET_REGIME"].isna().any():
        raise ValueError("Invalid market regime values.")

    working_df["symbol"] = (
        working_df["symbol"].astype(str).str.strip()
    )

    working_df["MARKET_REGIME"] = (
        working_df["MARKET_REGIME"].astype(str).str.strip()
    )

    if (
        (working_df["symbol"] == "").any()
        or (working_df["MARKET_REGIME"] == "").any()
    ):
        raise ValueError("Empty symbols or regimes found.")

    if working_df.duplicated(["timestamp", "symbol"]).any():
        raise ValueError("Duplicate regime timestamp and symbol.")

    regime_lookup = working_df.set_index(
        ["timestamp", "symbol"]
    )["MARKET_REGIME"]

    # Validate and match each trade.
    matched_trades = []

    for trade in trades:

        if not isinstance(trade, dict):
            raise ValueError("Invalid trade record.")

        required_trade_fields = {
            "symbol",
            "entry_time",
            "net_pnl",
            "total_cost",
            "entry",
            "quantity"
        }

        if not required_trade_fields.issubset(trade):
            raise ValueError("Missing trade metrics.")

        timestamp = pd.to_datetime(
            trade["entry_time"],
            errors="coerce"
        )

        if pd.isna(timestamp):
            raise ValueError("Invalid trade entry timestamp.")

        symbol = str(trade["symbol"]).strip()

        if not symbol:
            raise ValueError("Invalid trade symbol.")

        numeric_fields = [
            "net_pnl",
            "total_cost",
            "entry",
            "quantity"
        ]

        values = {}

        for field in numeric_fields:
            value = trade[field]

            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                raise ValueError(f"Invalid trade {field}.")

            values[field] = value

        if values["total_cost"] < 0 or values["entry"] <= 0:
            raise ValueError("Invalid trade cost or entry price.")

        if values["quantity"] <= 0:
            raise ValueError("Trade quantity must be positive.")

        key = (timestamp, symbol)

        regime = regime_lookup.get(key, "UNKNOWN")

        matched_trades.append({
            "symbol": symbol,
            "entry_time": timestamp,
            "market_regime": regime,
            "net_pnl": values["net_pnl"],
            "total_cost": values["total_cost"],
            "entry_value": values["entry"] * values["quantity"]
        })

    # Calculate metrics for every observed regime.
    observed_regimes = set(
        working_df["MARKET_REGIME"].tolist()
    )

    observed_regimes.add("UNKNOWN")

    grouped = {}

    for regime in observed_regimes:

        regime_trades = [
            trade for trade in matched_trades
            if trade["market_regime"] == regime
        ]

        winners = [
            trade for trade in regime_trades
            if trade["net_pnl"] > 0
        ]

        losers = [
            trade for trade in regime_trades
            if trade["net_pnl"] < 0
        ]

        breakeven = [
            trade for trade in regime_trades
            if trade["net_pnl"] == 0
        ]

        total_trades = len(regime_trades)

        net_pnl = sum(
            trade["net_pnl"]
            for trade in regime_trades
        )

        winning_pnl = sum(
            trade["net_pnl"]
            for trade in winners
        )

        losing_pnl = abs(sum(
            trade["net_pnl"]
            for trade in losers
        ))

        total_costs = sum(
            trade["total_cost"]
            for trade in regime_trades
        )

        total_entry_value = sum(
            trade["entry_value"]
            for trade in regime_trades
        )

        grouped[regime] = {
            "market_regime": regime,
            "total_trades": total_trades,
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "breakeven_trades": len(breakeven),
            "net_pnl": round(net_pnl, 2),
            "total_costs": round(total_costs, 2),
            "win_rate": round(
                len(winners) / total_trades * 100,
                2
            ) if total_trades else 0,
            "average_net_pnl": round(
                net_pnl / total_trades,
                2
            ) if total_trades else 0,
            "average_trade_return_percent": round(
                net_pnl / total_entry_value * 100,
                4
            ) if total_entry_value else 0,
            "profit_factor": round(
                winning_pnl / losing_pnl,
                2
            ) if losing_pnl else (
                None if winning_pnl == 0 else None
            )
        }

    results = sorted(
        grouped.values(),
        key=lambda item: item["net_pnl"],
        reverse=True
    )

    traded_regimes = [
        item for item in results
        if item["total_trades"] > 0
    ]

    best_regime = (
        max(traded_regimes, key=lambda item: item["net_pnl"])
        if traded_regimes else None
    )

    worst_regime = (
        min(traded_regimes, key=lambda item: item["net_pnl"])
        if traded_regimes else None
    )

    return {
        "total_trades_analyzed": len(matched_trades),
        "best_regime": best_regime,
        "worst_regime": worst_regime,
        "regime_performance": results,
        "unmatched_trades": sum(
            1 for trade in matched_trades
            if trade["market_regime"] == "UNKNOWN"
        )
    }
