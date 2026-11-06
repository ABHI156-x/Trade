
from datetime import time


MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)

ENTRY_CUTOFF = time(15, 15)
SQUARE_OFF_TIME = time(15, 25)


def is_market_session(timestamp):
    current_time = timestamp.time()

    return MARKET_OPEN <= current_time <= MARKET_CLOSE


def is_entry_allowed(timestamp):
    current_time = timestamp.time()

    return MARKET_OPEN <= current_time <= ENTRY_CUTOFF


def is_square_off_time(timestamp):
    return timestamp.time() >= SQUARE_OFF_TIME
