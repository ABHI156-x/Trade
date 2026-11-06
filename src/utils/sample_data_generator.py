
import pandas as pd
import random
from datetime import datetime, timedelta


def generate_sample_data():
    random.seed(42)

    stocks = {
        "RELIANCE": 1400,
        "TCS": 3000,
        "INFY": 1500,
        "HDFCBANK": 1700,
        "ICICIBANK": 1200
    }

    all_data = []

    for symbol, starting_price in stocks.items():

        price = starting_price

        # Generate 60 five-minute candles
        for i in range(60):

            change = random.uniform(-8, 8)

            open_price = price
            close_price = max(1, open_price + change)

            high_price = max(open_price, close_price) + random.uniform(1, 5)
            low_price = min(open_price, close_price) - random.uniform(1, 5)

            volume = random.randint(10000, 50000)

            timestamp = datetime(2026, 11, 4, 9, 15) + timedelta(minutes=5 * i)

            all_data.append({
                "timestamp": timestamp,
                "symbol": symbol,
                "exchange": "NSE",
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": volume
            })

            price = close_price

    df = pd.DataFrame(all_data)

    df.to_csv("data/sample_nse_5m.csv", index=False)

    print("Sample market data generated successfully!")
    print("Total candles:", len(df))
    print("Total stocks:", df["symbol"].nunique())


if __name__ == "__main__":
    generate_sample_data()
