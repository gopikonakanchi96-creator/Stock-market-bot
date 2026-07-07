from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from trading_bot.notifications.email_service import EmailService
from trading_bot.reporting.daily_report import DailyReportBuilder
from trading_bot.app.domain import Instrument, OrderResult, Position as DomainPosition, SignalAction, StrategyDecision
from trading_bot.database.models import Base
from trading_bot.database.repositories import TradingRepository


def test_daily_report_handles_no_trade_day(tmp_path):
    builder = DailyReportBuilder()
    report = builder.build(
        recipient="gkkcsp2023@gmail.com",
        orders=[],
        balances={"USD": 100_000, "INR": 1_000_000},
        portfolio_value_base=100_000,
        us_market_status="closed",
    )

    text = builder.to_text(report)

    assert "No trades were placed today" in text
    assert "USD: 100000.00" in text
    assert "US market status: closed" in text


def test_email_service_reports_missing_smtp(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for key in ["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL"]:
        monkeypatch.delenv(key, raising=False)

    result = EmailService().send_report("gkkcsp2023@gmail.com", "test", "body")

    assert result.sent is False
    assert "SMTP is not configured" in result.reason


def test_daily_report_reads_from_repository():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    repo = TradingRepository(sessionmaker(bind=engine, expire_on_commit=False))
    decision = StrategyDecision(SignalAction.WAIT, 0.5, "market closed", 0, 0)
    instrument = Instrument("AAPL", "Apple", "US", "United States", "NASDAQ", "USD")

    repo.log_signal("AAPL", decision)
    repo.log_risk_event("warning", "Market is closed")
    order_id = repo.log_order_result("AAPL", "BUY", 2, 100, "USD", "test", OrderResult("paper-1", True, "filled", "ok", 100))
    repo.log_trade(order_id, realized_pl=12.5)
    repo.upsert_position(DomainPosition(instrument, 2, 100, 110, 110, 90, 103))
    repo.log_portfolio_history("USD", 100_012.5)

    report = DailyReportBuilder().build_from_repository(
        repo,
        recipient="gkkcsp2023@gmail.com",
        balances={"USD": 100_000},
        us_market_status="closed",
        report_date=datetime.utcnow().date(),
    )
    text = DailyReportBuilder().to_text(report)

    assert report.orders[0].pnl == 12.5
    assert report.signal_counts["WAIT"] == 1
    assert report.open_positions[0]["symbol"] == "AAPL"
    assert "Market is closed" in text
