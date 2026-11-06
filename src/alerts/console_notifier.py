"""
Stage 25 – Console / Log Notifier
Prints alert messages to stdout and the system logger.
"""

import sys
from datetime import datetime


class ConsoleNotifier:
    """
    Writes alert messages to stdout with a severity prefix.
    Optionally also writes to a logger instance.

    Parameters
    ----------
    logger : logging.Logger or None – if provided, messages are also logged.
    """

    def __init__(self, logger=None):
        self.logger = logger

    def _format(self, level: str, message: str) -> str:
        ts = datetime.now().strftime("%H:%M:%S")
        return f"[{ts}] [{level}] {message}"

    def send(self, message: str, level: str = "INFO"):
        line = self._format(level.upper(), message)
        print(line, file=sys.stdout, flush=True)

        if self.logger:
            log_fn = getattr(self.logger, level.lower(), self.logger.info)
            log_fn(message)

        return line
