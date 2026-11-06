
from src.risk.trading_costs import calculate_trading_costs


def calculate_unrealized_pnl(
    position,
    current_price,
    brokerage_per_order=5,
    charges_rate=0.001,
    slippage_per_share=0.50
):
    """
    Calculate estimated unrealized P&L after trading costs
    for an open long position.
    """

    if not isinstance(position, dict):
        raise TypeError("Position must be a dictionary.")

    required = ["entry", "quantity"]

    for key in required:
        if key not in position:
            raise ValueError(f"Position is missing: {key}")

    result = calculate_trading_costs(
        entry_price=position["entry"],
        exit_price=current_price,
        quantity=position["quantity"],
        brokerage_per_order=brokerage_per_order,
        charges_rate=charges_rate,
        slippage_per_share=slippage_per_share
    )

    return result["net_pnl"]
