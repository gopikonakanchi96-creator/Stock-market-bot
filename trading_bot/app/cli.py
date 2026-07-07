from __future__ import annotations

import argparse
import json
import os

from trading_bot.app.paper_session import run_sample_paper_session
from trading_bot.backtesting.engine import sample_backtest
from trading_bot.brokers.connection_check import check_alpaca_paper_connection
from trading_bot.config.env import load_env_file
from trading_bot.config.settings import load_settings
from trading_bot.database.repositories import TradingRepository
from trading_bot.market_data.service import EnterpriseMarketDataService
from trading_bot.notifications import EmailService
from trading_bot.reporting import DailyReportBuilder, MarketSummary


def _market_summaries(settings, service: EnterpriseMarketDataService) -> list[MarketSummary]:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="AI multi-currency trading bot")
    parser.add_argument(
        "--mode",
        choices=[
            "paper-sample",
            "backtest",
            "check-alpaca",
            "check-market-data",
            "send-daily-report",
            "send-weekly-report",
            "send-monthly-report",
            "send-quarterly-report",
        ],
        default="paper-sample",
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--market", default="US")
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--to", default="gkkcsp2023@gmail.com")
    parser.add_argument("--persist", action="store_true", help="Write runtime decisions to PostgreSQL")
    args = parser.parse_args()
    if args.mode == "check-alpaca":
        print(json.dumps(check_alpaca_paper_connection(), indent=2))
    elif args.mode == "check-market-data":
        load_env_file()
        settings = load_settings(args.config)
        market = settings.markets[args.market]
        service = EnterpriseMarketDataService(settings.strategy, settings.market_data_provider_priority)
        indicators = service.indicators(args.symbol, market)
        print(
            json.dumps(
                {
                    "symbol": args.symbol,
                    "market": args.market,
                    "exchange_status": service.exchange_status(market),
                    "provider_used": service.last_provider_name,
                    "provider_errors_before_success": service.last_provider_errors,
                    "indicators": indicators.__dict__ if indicators else None,
                    "data_available": indicators is not None,
                },
                indent=2,
                default=str,
            )
        )
    elif args.mode == "backtest":
        print(json.dumps(sample_backtest().__dict__, indent=2))
    elif args.mode in {"send-daily-report", "send-weekly-report", "send-monthly-report", "send-quarterly-report"}:
        load_env_file()
        settings = load_settings(args.config)
        market_service = EnterpriseMarketDataService(settings.strategy, settings.market_data_provider_priority)
        us_status = market_service.exchange_status(settings.markets["US"])
        report_type = args.mode.removeprefix("send-").removesuffix("-report")
        builder = DailyReportBuilder()
        report = builder.build_from_repository(
            repository=TradingRepository.from_config(args.config),
            recipient=args.to,
            balances=settings.paper_starting_balances,
            base_currency=settings.base_currency,
            us_market_status="open" if us_status["is_open"] else "closed",
            market_summaries=_market_summaries(settings, market_service),
            report_type=report_type,
            timezone_name=os.getenv("REPORT_TIMEZONE", "America/Chicago"),
        )
        pdf_path = builder.write_pdf(report)
        result = EmailService().send_report(
            to_email=args.to,
            subject=f"{report.report_type.title()} Trading Review - {report.report_date.isoformat()}",
            body=builder.to_text(report),
            attachment_path=pdf_path,
        )
        print(
            json.dumps(
                {
                    "recipient": args.to,
                    "pdf": str(pdf_path),
                    "email_sent": result.sent,
                    "reason": result.reason,
                },
                indent=2,
            )
        )
    else:
        print(json.dumps(run_sample_paper_session(args.config, enable_repository=args.persist), indent=2, default=str))


if __name__ == "__main__":
    main()
