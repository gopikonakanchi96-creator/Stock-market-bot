from trading_bot.app.automation import automation_health


def test_automation_health_registers_expected_jobs():
    status = automation_health()

    assert status["mode"] == "paper"
    assert status["paper_trading"] is True
    assert status["live_trading"] is False
    assert "paper_market_scan" in status["scheduler_jobs"]
    assert "daily_trading_review" in status["scheduler_jobs"]
    assert "weekly_trading_review" in status["scheduler_jobs"]
    assert "monthly_trading_review" in status["scheduler_jobs"]
    assert "quarterly_trading_review" in status["scheduler_jobs"]
