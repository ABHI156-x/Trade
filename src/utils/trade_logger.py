
import logging
from pathlib import Path


def get_trade_logger(log_file="logs/trading.log"):

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("indian_day_trader")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Reuse a handler only when it points to the requested file.
    for handler in logger.handlers[:]:

        if isinstance(handler, logging.FileHandler):

            if Path(handler.baseFilename).resolve() == log_path.resolve():
                return logger

            logger.removeHandler(handler)
            handler.close()

        else:
            logger.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler = logging.FileHandler(
        log_path,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def close_trade_logger():

    logger = logging.getLogger("indian_day_trader")

    for handler in logger.handlers[:]:
        handler.flush()
        handler.close()
        logger.removeHandler(handler)
