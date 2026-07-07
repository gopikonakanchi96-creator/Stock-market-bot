from __future__ import annotations

import json
import signal
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

from trading_bot.app.paper_session import build_application_context
from trading_bot.config.env import load_env_file
from trading_bot.config.settings import AppSettings, load_settings
from trading_bot.database.repositories import TradingRepository
from trading_bot.market_data.service import EnterpriseMarketDataService
from trading_bot.monitoring.logging import configure_logging, get_logger
from trading_bot.notifications import EmailService
from trading_bot.reporting import DailyReportBuilder, MarketSummary


@dataclass(frozen=True)
class AutomationStatus:
    mode: str
    paper_trading: bool
    live_trading: bool
    emergency_stop: bool
    scan_interval_minutes: int
    run_outside_market_hours: bool
    report_to: str
    timezone: str
    scheduler_jobs: list[str]


def market_summaries(settings: AppSettings, service: EnterpriseMarketDataService) -> list[MarketSummary]:
    summaries: list[MarketSummary] = []
    for market_code, market in settings.markets.items():
        if not market.enabled:
            continue
        for symbol in settings.watchlists.get(market_code, [])[:8]:
            indicators = service.indicators(symbol, market)
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
                    provider=service.last_provider_name,
                )
            )
    return summaries


class TradingAutomationRunner:
    def __init__(self, config_path: str = "config.yaml") -> None:
        load_env_file()
        configure_logging()
        self.config_path = config_path
        self.settings = load_settings(config_path)
        self.logger = get_logger("automation")
        self.scheduler = BackgroundScheduler(timezone=self.settings.automation.timezone)
        self._stopped = False

    def status(self) -> AutomationStatus:
        return AutomationStatus(
            mode="paper",
            paper_trading=self.settings.paper_trading,
            live_trading=self.settings.live_trading,
            emergency_stop=self.settings.risk.emergency_stop,
            scan_interval_minutes=self.settings.automation.scan_interval_minutes,
            run_outside_market_hours=self.settings.automation.run_outside_market_hours,
            report_to=self.settings.automation.report_to,
            timezone=self.settings.automation.timezone,
            scheduler_jobs=[job.id for job in self.scheduler.get_jobs()],
        )

    def run_once(self) -> list[dict[str, object]]:
        context = build_application_context(self.config_path, enable_repository=True)
        settings: AppSettings = context["settings"]
        market_data: EnterpriseMarketDataService = context["market_data"]
        open_markets = [
            market.code
            for market in settings.markets.values()
            if market.enabled and market_data.market_is_open(market)
        ]
        if not open_markets and not settings.automation.run_outside_market_hours:
            self.logger.info("automation_scan_skipped", reason="all enabled markets are closed")
            return []
        self.logger.info("automation_scan_started", open_markets=open_markets)
        decisions = context["paper_session"].run_once()
        self.logger.info("automation_scan_finished", decisions=len(decisions))
        return decisions

    def send_report(self, report_type: str) -> dict[str, Any]:
        context = build_application_context(self.config_path)
        settings: AppSettings = context["settings"]
        market_data: EnterpriseMarketDataService = context["market_data"]
        us_status = market_data.exchange_status(settings.markets["US"])
        builder = DailyReportBuilder()
        report = builder.build_from_repository(
            repository=TradingRepository.from_config(self.config_path),
            recipient=settings.automation.report_to,
            balances=settings.paper_starting_balances,
            base_currency=settings.base_currency,
            us_market_status="open" if us_status["is_open"] else "closed",
            market_summaries=market_summaries(settings, market_data),
            report_type=report_type,
            timezone_name=settings.automation.timezone,
        )
        pdf_path = builder.write_pdf(report)
        result = EmailService().send_report(
            to_email=report.recipient,
            subject=f"{report.report_type.title()} Trading Review - {report.report_date.isoformat()}",
            body=builder.to_text(report),
            attachment_path=pdf_path,
        )
        payload = {
            "report_type": report_type,
            "recipient": report.recipient,
            "pdf": str(pdf_path),
            "email_sent": result.sent,
            "reason": result.reason,
        }
        self.logger.info("automation_report_sent", **payload)
        return payload

    def start(self) -> None:
        if self.settings.live_trading:
            raise RuntimeError("Automation refuses to run live trading in Version 1. Keep live_trading=false.")
        if not self.settings.paper_trading:
            raise RuntimeError("Automation requires paper_trading=true.")
        self._register_jobs()
        self.scheduler.start()
        status = self.status()
        print(json.dumps(status.__dict__, indent=2))
        self.logger.info("automation_started", **status.__dict__)
        self._install_signal_handlers()
        try:
            while not self._stopped:
                time.sleep(1)
        finally:
            self.scheduler.shutdown(wait=False)
            self.logger.info("automation_stopped")

    def _register_jobs(self) -> None:
        interval = max(1, self.settings.automation.scan_interval_minutes)
        self.scheduler.add_job(
            self.run_once,
            trigger="interval",
            minutes=interval,
            id="paper_market_scan",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.add_job(
            lambda: self.send_report("daily"),
            trigger="cron",
            hour=self.settings.automation.daily_report_hour,
            minute=self.settings.automation.daily_report_minute,
            id="daily_trading_review",
            replace_existing=True,
        )
        self.scheduler.add_job(
            lambda: self.send_report("weekly"),
            trigger="cron",
            day_of_week=self.settings.automation.weekly_report_day,
            hour=self.settings.automation.daily_report_hour,
            minute=self.settings.automation.daily_report_minute + 5,
            id="weekly_trading_review",
            replace_existing=True,
        )
        self.scheduler.add_job(
            lambda: self.send_report("monthly"),
            trigger="cron",
            day="last",
            hour=self.settings.automation.daily_report_hour,
            minute=self.settings.automation.daily_report_minute + 10,
            id="monthly_trading_review",
            replace_existing=True,
        )
        self.scheduler.add_job(
            lambda: self.send_report("quarterly"),
            trigger="cron",
            month="3,6,9,12",
            day="last",
            hour=self.settings.automation.daily_report_hour,
            minute=self.settings.automation.daily_report_minute + 15,
            id="quarterly_trading_review",
            replace_existing=True,
        )

    def _install_signal_handlers(self) -> None:
        def stop_handler(signum, frame) -> None:  # type: ignore[no-untyped-def]
            self._stopped = True

        signal.signal(signal.SIGINT, stop_handler)
        signal.signal(signal.SIGTERM, stop_handler)


def run_automation(config_path: str = "config.yaml") -> None:
    TradingAutomationRunner(config_path).start()


def automation_health(config_path: str = "config.yaml") -> dict[str, Any]:
    runner = TradingAutomationRunner(config_path)
    runner._register_jobs()
    status = runner.status().__dict__
    status["current_date"] = date.today().isoformat()
    return status
