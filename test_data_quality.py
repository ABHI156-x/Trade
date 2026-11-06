
from src.market_data.data_loader import load_market_data

from src.market_data.data_quality import (
    check_market_data_quality,
    print_data_quality_report
)


df = load_market_data("data/sample_nse_5m.csv")

report = check_market_data_quality(
    df,
    interval_minutes=5
)

print_data_quality_report(report)
