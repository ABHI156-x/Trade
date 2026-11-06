"""
Stage 28 – Post-Market Tasks
Runs after the trading session: generate summary report and save trade journal.
"""

import csv
import json
from pathlib import Path
from datetime import date, datetime


def run_post_market_tasks(
    broker_report=None,
    risk_report=None,
    journal_dir="data",
    reports_dir="logs",
    logger=None
):
    """
    Execute post-market wrap-up tasks:
      1. Save trade journal to CSV
      2. Write daily summary JSON report
      3. Log completion

    Parameters
    ----------
    broker_report : dict from PortfolioPaperBroker.get_report()
    risk_report   : dict from DailyRiskGuard.get_report()
    journal_dir   : str – directory for trade_journal.csv
    reports_dir   : str – directory for daily reports
    logger        : logging.Logger

    Returns
    -------
    dict with paths to saved files
    """
    today = date.today()

    def log(msg, level="info"):
        if logger:
            getattr(logger, level)(msg)
        print(f"[POST-MARKET] {msg}")

    log(f"Post-market tasks starting for {today}")

    saved = {}

    Path(journal_dir).mkdir(parents=True, exist_ok=True)
    Path(reports_dir).mkdir(parents=True, exist_ok=True)

    # Save trade journal CSV
    if broker_report and broker_report.get("completed_trades", 0) > 0:
        journal_file = Path(journal_dir) / "trade_journal.csv"
        trade_history = broker_report.get("trade_history", [])

        if trade_history:
            fieldnames = list(trade_history[0].keys()) if trade_history else []

            with open(journal_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if journal_file.stat().st_size == 0:
                    writer.writeheader()
                for trade in trade_history:
                    flat = {
                        k: (v if not isinstance(v, dict) else json.dumps(v))
                        for k, v in trade.items()
                    }
                    writer.writerow(flat)

            log(f"Trade journal updated: {journal_file}")
            saved["journal"] = str(journal_file)

    # Save daily summary report
    report_file = (
        Path(reports_dir) / f"daily_report_{today}.json"
    )

    summary = {
        "date":           str(today),
        "generated_at":   datetime.now().isoformat(timespec="seconds"),
        "broker_report":  broker_report or {},
        "risk_report":    risk_report or {},
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    log(f"Daily report saved: {report_file}")
    saved["report"] = str(report_file)

    log("Post-market tasks complete")
    return saved
