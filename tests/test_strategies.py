
import unittest
import pandas as pd

from src.analysis.strategies import (
    generate_ema_crossover_signals,
    get_ema_strategy_configs
)


class TestEMAStrategies(unittest.TestCase):

    def test_bullish_crossover(self):

        df = pd.DataFrame({
            "EMA_9": [9, 11],
            "EMA_21": [10, 10]
        })

        result = generate_ema_crossover_signals(df)

        self.assertEqual(
            result.iloc[1]["strategy_signal"],
            "BUY"
        )

    def test_bearish_crossover(self):

        df = pd.DataFrame({
            "EMA_9": [11, 9],
            "EMA_21": [10, 10]
        })

        result = generate_ema_crossover_signals(df)

        self.assertEqual(
            result.iloc[1]["strategy_signal"],
            "SELL"
        )

    def test_no_crossover(self):

        df = pd.DataFrame({
            "EMA_9": [11, 12],
            "EMA_21": [10, 10]
        })

        result = generate_ema_crossover_signals(df)

        self.assertEqual(
            result.iloc[1]["strategy_signal"],
            "NEUTRAL"
        )

    def test_custom_ema_periods(self):

        df = pd.DataFrame({
            "EMA_5": [9, 11],
            "EMA_20": [10, 10]
        })

        result = generate_ema_crossover_signals(
            df,
            fast_period=5,
            slow_period=20
        )

        self.assertEqual(
            result.iloc[1]["strategy_signal"],
            "BUY"
        )

    def test_invalid_periods(self):

        df = pd.DataFrame({
            "EMA_9": [9, 11],
            "EMA_21": [10, 10]
        })

        with self.assertRaises(ValueError):

            generate_ema_crossover_signals(
                df,
                fast_period=21,
                slow_period=9
            )

    def test_strategy_configs(self):

        configs = get_ema_strategy_configs()

        self.assertEqual(len(configs), 4)

        self.assertEqual(
            configs[0]["name"],
            "EMA 5/20"
        )


if __name__ == "__main__":
    unittest.main()
