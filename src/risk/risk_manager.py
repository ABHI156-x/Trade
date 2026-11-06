
def calculate_position_size(
    entry_price,
    stop_loss,
    target_price,
    available_capital,
    risk_per_trade,
    daily_loss=0,
    max_daily_loss=500
):
    # Validate inputs
    if min(entry_price, stop_loss, target_price,
           available_capital, risk_per_trade, max_daily_loss) <= 0:
        raise ValueError("All prices and limits must be positive.")

    if daily_loss < 0:
        raise ValueError("Daily loss cannot be negative.")

    if not (stop_loss < entry_price < target_price):
        raise ValueError("For a long trade, stop must be below entry and target above entry.")

    # Check remaining daily risk budget
    remaining_daily_risk = max_daily_loss - daily_loss

    if remaining_daily_risk <= 0:
        return {
            "status": "BLOCKED",
            "reason": "Daily loss limit reached."
        }

    # Calculate risk per share
    risk_per_share = entry_price - stop_loss

    # Calculate reward per share
    reward_per_share = target_price - entry_price

    # Use the smaller of trade risk and remaining daily risk
    allowed_risk = min(risk_per_trade, remaining_daily_risk)

    # Calculate quantity using risk and capital limits
    risk_quantity = int(allowed_risk // risk_per_share)
    capital_quantity = int(available_capital // entry_price)

    quantity = min(risk_quantity, capital_quantity)

    if quantity <= 0:
        return {
            "status": "BLOCKED",
            "reason": "Insufficient capital or risk budget."
        }

    # Final calculations
    total_investment = quantity * entry_price
    total_risk = quantity * risk_per_share
    potential_profit = quantity * reward_per_share

    risk_reward = reward_per_share / risk_per_share

    return {
        "status": "APPROVED_FOR_PAPER_TEST",
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "target": target_price,
        "quantity": quantity,
        "investment": total_investment,
        "risk": total_risk,
        "potential_profit": potential_profit,
        "risk_reward": round(risk_reward, 2)
    }
