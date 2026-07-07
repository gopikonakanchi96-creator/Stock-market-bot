from __future__ import annotations

import os

from apscheduler.schedulers.background import BackgroundScheduler

from trading_bot.app.paper_session import build_application_context
from trading_bot.database.repositories import TradingRepository
from trading_bot.notifications import EmailService
from trading_bot.reporting import DailyReportBuilder, MarketSummary


def _market_summaries(settings, market_service) -> list[MarketSummary]:
    summaries: list[MarketSummary] = []
    for market_code, market in settings.markets.items():
        if not market.enabled:
            continue
        for symbol in settings.watchlists.get(market_code, [])[:8]:
            indicators = market_service.indicators(symbol, market)
            if indicators is None or indicators.previous_close <= 0 or indicators.average_volume <= 0:
                continue
            summaries.append(
                MarketSummary(
                    market=market_code,
                    symbol=symbol,
                    current_price=indicators.current_price,
                    daily_change_pct=(
                        (indicators.current_price - indicators.previous_close) / indicators.previous_close
                    )
                    * 100,
                    volume_ratio=indicators.volume / indicators.average_volume,
                    rsi=indicators.rsi,
                    trend=indicators.trend,
                    macd=indicators.macd,
                    macd_signal=indicators.macd_signal,
                    provider=market_service.last_provider_name,
                )
            )
    return summaries


def create_daily_report_scheduler(config_path: str = "config.yaml") -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=os.getenv("REPORT_TIMEZONE", "America/Chicago"))

    def send_report_job() -> None:
        context = build_application_context(config_path)
        settings = context["settings"]
        market_service = context["market_data"]
        us_status = market_service.exchange_status(settings.markets["US"])
        builder = DailyReportBuilder()
        report = builder.build_from_repository(
            repository=TradingRepository.from_config(config_path),
            recipient=os.getenv("DAILY_REPORT_TO", "gkkcsp2023@gmail.com"),
            balances=settings.paper_starting_balances,
            base_currency=settings.base_currency,
            us_market_status="open" if us_status["is_open"] else "closed",
            market_summaries=_market_summaries(settings, market_service),
            timezone_name=os.getenv("REPORT_TIMEZONE", "America/Chicago"),
        )
        pdf_path = builder.write_pdf(report)
        EmailService().send_report(
            report.recipient,
            f"Daily Trading Review - {report.report_date.isoformat()}",
            builder.to_text(report),
            pdf_path,
        )

    scheduler.add_job(
        send_report_job,
        trigger="cron",
        hour=int(os.getenv("DAILY_REPORT_HOUR", "17")),
        minute=int(os.getenv("DAILY_REPORT_MINUTE", "0")),
        id="daily_trading_report",
        replace_existing=True,
    )
    return scheduler
