"""
Stage 28 – Job Scheduler
APScheduler-based daily task runner.
Fires pre_market_tasks at 09:00 IST and post_market_tasks at 16:00 IST.
Respects the NSE market calendar (skips weekends and holidays).
"""

from datetime import datetime
from src.utils.market_calendar import is_trading_day


def _should_run_today(exchange="NSE") -> bool:
    return is_trading_day(datetime.now().date(), exchange)


def create_scheduler(
    symbols=None,
    exchange="NSE",
    data_dir="data",
    reports_dir="logs",
    logger=None
):
    """
    Build and return a configured APScheduler BlockingScheduler.

    Jobs registered
    ---------------
    - pre_market  : daily at 09:00 Asia/Kolkata
    - post_market : daily at 16:00 Asia/Kolkata

    Parameters
    ----------
    symbols     : list – symbols to monitor
    exchange    : str  – "NSE" or "BSE"
    data_dir    : str  – directory for market data CSV files
    reports_dir : str  – directory for daily report JSON files
    logger      : logging.Logger – system logger

    Returns
    -------
    APScheduler BlockingScheduler instance (not yet started)
    """
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError:
        raise ImportError(
            "apscheduler is required. Install with: pip install apscheduler"
        )

    from src.scheduler.pre_market_tasks  import run_pre_market_tasks
    from src.scheduler.post_market_tasks import run_post_market_tasks

    scheduler = BlockingScheduler(timezone="Asia/Kolkata")

    def _pre_market_job():
        if not _should_run_today(exchange):
            if logger:
                logger.info("Today is not a trading day. Skipping pre-market tasks.")
            return
        run_pre_market_tasks(
            symbols=symbols,
            data_dir=data_dir,
            exchange=exchange,
            logger=logger
        )

    def _post_market_job():
        if not _should_run_today(exchange):
            return
        run_post_market_tasks(
            broker_report=None,
            risk_report=None,
            journal_dir=data_dir,
            reports_dir=reports_dir,
            logger=logger
        )

    scheduler.add_job(
        _pre_market_job,
        trigger="cron",
        hour=9,
        minute=0,
        id="pre_market",
        replace_existing=True
    )

    scheduler.add_job(
        _post_market_job,
        trigger="cron",
        hour=16,
        minute=0,
        id="post_market",
        replace_existing=True
    )

    return scheduler
