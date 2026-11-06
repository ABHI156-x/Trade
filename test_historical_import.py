
from src.market_data.csv_importer import import_historical_csv


df = import_historical_csv(
    "data/sample_nse_5m.csv"
)

print("\nHISTORICAL DATA IMPORT REPORT")
print("=" * 45)

print("Total candles:", len(df))
print("Total symbols:", df["symbol"].nunique())
print("Symbols:", ", ".join(sorted(df["symbol"].unique())))

print("\nFirst 5 candles:")
print(df.head().to_string(index=False))

print("\nLast 5 candles:")
print(df.tail().to_string(index=False))

print("\nHistorical import completed successfully.")
