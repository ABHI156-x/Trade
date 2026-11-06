
def calculate_trading_costs(
    entry_price,
    exit_price,
    quantity,
    brokerage_per_order=0,
    charges_rate=0,
    slippage_per_share=0
):
    if min(entry_price, exit_price, quantity) <= 0:
        raise ValueError("Prices and quantity must be positive.")

    if min(brokerage_per_order, charges_rate, slippage_per_share) < 0:
        raise ValueError("Costs cannot be negative.")

    turnover = (entry_price + exit_price) * quantity

    brokerage = brokerage_per_order * 2
    other_charges = turnover * charges_rate

    slippage = slippage_per_share * quantity * 2

    total_cost = brokerage + other_charges + slippage

    gross_pnl = (exit_price - entry_price) * quantity
    net_pnl = gross_pnl - total_cost

    return {
        "gross_pnl": round(gross_pnl, 2),
        "brokerage": round(brokerage, 2),
        "other_charges": round(other_charges, 2),
        "slippage": round(slippage, 2),
        "total_cost": round(total_cost, 2),
        "net_pnl": round(net_pnl, 2)
    }


import math


def calculate_indian_equity_intraday_costs(
    entry_price,
    exit_price,
    quantity,
    exchange="NSE",
    slippage_per_share=0.05,
    brokerage_rate=0.001,
    brokerage_cap=20,
    brokerage_minimum=5,
    brokerage_minimum_rate=0.025,
    stt_sell_rate=0.00025,
    stamp_duty_buy_rate=0.00003,
    exchange_transaction_rate=None,
    sebi_turnover_rate=0.000001,
    ipft_rate=None,
    gst_rate=0.18
):
    """
    Estimate Indian equity intraday trading costs.

    This is a configurable Groww-style cost model.
    It is a simulation estimate, not a contract-note calculator.
    """

    values = [
        entry_price, exit_price, quantity,
        slippage_per_share, brokerage_rate,
        brokerage_cap, brokerage_minimum,
        brokerage_minimum_rate, stt_sell_rate,
        stamp_duty_buy_rate, sebi_turnover_rate,
        gst_rate
    ]

    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("All inputs must be finite numbers")

    if min(entry_price, exit_price, quantity) <= 0:
        raise ValueError("Prices and quantity must be positive")

    if int(quantity) != quantity:
        raise ValueError("Quantity must be a whole number")

    if min(values[3:]) < 0:
        raise ValueError("Cost rates and amounts cannot be negative")

    exchange = exchange.upper()

    if exchange not in ("NSE", "BSE"):
        raise ValueError("Exchange must be NSE or BSE")

    if exchange_transaction_rate is None:
        exchange_transaction_rate = {
            "NSE": 0.0000297,
            "BSE": 0.0000375
        }

    if ipft_rate is None:
        ipft_rate = {
            "NSE": 0.000001,
            "BSE": 0
        }

    for rate in [
        exchange_transaction_rate.get(exchange),
        ipft_rate.get(exchange)
    ]:
        if rate is None or not math.isfinite(float(rate)) or rate < 0:
            raise ValueError("Invalid exchange charge rate")

    buy_turnover = float(entry_price) * quantity
    sell_turnover = float(exit_price) * quantity
    total_turnover = buy_turnover + sell_turnover

    def calculate_brokerage(order_value):
        normal_charge = min(
            brokerage_cap,
            order_value * brokerage_rate
        )

        minimum_charge = min(
            brokerage_minimum,
            order_value * brokerage_minimum_rate
        )

        return max(normal_charge, minimum_charge)

    brokerage_buy = calculate_brokerage(buy_turnover)
    brokerage_sell = calculate_brokerage(sell_turnover)

    brokerage = brokerage_buy + brokerage_sell

    stt = sell_turnover * stt_sell_rate
    stamp_duty = buy_turnover * stamp_duty_buy_rate

    exchange_charges = (
        total_turnover * exchange_transaction_rate[exchange]
    )

    sebi_charges = total_turnover * sebi_turnover_rate

    ipft_charges = total_turnover * ipft_rate[exchange]

    taxable_charges = (
        brokerage
        + exchange_charges
        + sebi_charges
        + ipft_charges
    )

    gst = taxable_charges * gst_rate

    slippage = quantity * 2 * slippage_per_share

    total_cost = (
        brokerage
        + stt
        + stamp_duty
        + exchange_charges
        + sebi_charges
        + ipft_charges
        + gst
        + slippage
    )

    gross_pnl = (exit_price - entry_price) * quantity
    net_pnl = gross_pnl - total_cost

    return {
        "exchange": exchange,
        "buy_turnover": round(buy_turnover, 2),
        "sell_turnover": round(sell_turnover, 2),
        "brokerage_buy": round(brokerage_buy, 2),
        "brokerage_sell": round(brokerage_sell, 2),
        "brokerage": round(brokerage, 2),
        "stt": round(stt, 2),
        "stamp_duty": round(stamp_duty, 2),
        "exchange_charges": round(exchange_charges, 2),
        "sebi_charges": round(sebi_charges, 2),
        "ipft_charges": round(ipft_charges, 2),
        "gst": round(gst, 2),
        "slippage": round(slippage, 2),
        "total_cost": round(total_cost, 2),
        "gross_pnl": round(gross_pnl, 2),
        "net_pnl": round(net_pnl, 2)
    }

