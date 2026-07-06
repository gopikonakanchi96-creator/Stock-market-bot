from trading_bot.notifications.email_service import EmailService
from trading_bot.reporting.daily_report import DailyReportBuilder


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
