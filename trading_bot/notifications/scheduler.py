from __future__ import annotations

import os

from apscheduler.schedulers.background import BackgroundScheduler

from trading_bot.app.paper_session import build_application_context
from trading_bot.notifications import EmailService
from trading_bot.reporting import DailyReportBuilder


def create_daily_report_scheduler(config_path: str = "config.yaml") -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=os.getenv("REPORT_TIMEZONE", "America/Chicago"))

    def send_report_job() -> None:
        context = build_application_context(config_path)
        settings = context["settings"]
        market_service = context["market_data"]
        us_status = market_service.exchange_status(settings.markets["US"])
        builder = DailyReportBuilder()
        report = builder.build(
            recipient=os.getenv("DAILY_REPORT_TO", "gkkcsp2023@gmail.com"),
            balances=settings.paper_starting_balances,
            portfolio_value_base=settings.paper_starting_balances.get(settings.base_currency, 0.0),
            base_currency=settings.base_currency,
            us_market_status="open" if us_status["is_open"] else "closed",
        )
        pdf_path = builder.write_pdf(report)
        EmailService().send_report(report.recipient, f"Daily Trading Report - {report.report_date.isoformat()}", builder.to_text(report), pdf_path)

    scheduler.add_job(
        send_report_job,
        trigger="cron",
        hour=int(os.getenv("DAILY_REPORT_HOUR", "17")),
        minute=int(os.getenv("DAILY_REPORT_MINUTE", "0")),
        id="daily_trading_report",
        replace_existing=True,
    )
    return scheduler
