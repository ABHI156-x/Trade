
def check_exit_conditions(candle, position):

    stop = position["stop"]
    target = position["target"]

    open_price = candle["open"]
    high = candle["high"]
    low = candle["low"]

    # If the market opens below the stop,
    # assume the stop fills at the worse opening price.
    if open_price <= stop:
        return open_price, "STOP_LOSS_GAP"

    stop_hit = low <= stop
    target_hit = high >= target

    # Conservative assumption when both are touched.
    if stop_hit:
        return stop, "STOP_LOSS"

    if target_hit:
        return target, "TARGET"

    return None
