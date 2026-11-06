"""
Stage 26 – System Logger
Rotating-file system logger for errors, warnings and key events.
Creates logs/system.log with up to 3 × 5 MB backup files.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_system_logger(log_file: str = "logs/system.log") -> logging.Logger:
    """
    Return a named system logger with a rotating file handler.

    The logger is idempotent – calling this function twice with the same
    *log_file* returns the same logger without adding duplicate handlers.

    Parameters
    ----------
    log_file : path to the log file (parent dirs created automatically)

    Returns
    -------
    logging.Logger named "indian_day_trader.system"
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("indian_day_trader.system")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Avoid adding duplicate handlers for the same file
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler):
            if Path(handler.baseFilename).resolve() == log_path.resolve():
                return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Rotating file handler – 5 MB × 3 backups
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler shows WARNING and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def close_system_logger():
    """Flush and close all handlers on the system logger."""
    logger = logging.getLogger("indian_day_trader.system")
    for handler in logger.handlers[:]:
        handler.flush()
        handler.close()
        logger.removeHandler(handler)
