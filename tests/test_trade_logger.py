
import unittest
import tempfile
import logging
from pathlib import Path

from src.utils.trade_logger import get_trade_logger


class TestTradeLogger(unittest.TestCase):

    def test_logger_creates_log_file(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            log_file = Path(temp_dir) / "logs" / "test.log"

            logger = get_trade_logger(str(log_file))

            try:
                logger.info("Test trading event")

                for handler in logger.handlers:
                    handler.flush()

                self.assertTrue(log_file.exists())

                with open(log_file, "r", encoding="utf-8") as file:
                    content = file.read()

                self.assertIn("Test trading event", content)

            finally:
                # Close file handlers before Windows deletes the folder.
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
