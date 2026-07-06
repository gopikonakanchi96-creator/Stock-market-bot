from trading_bot.app.paper_session import build_application_context


def test_paper_session_can_analyze_enabled_us_symbol():
    context = build_application_context("config.yaml")
    result = context["paper_session"].analyze_symbol("US", "AAPL", execute=False)

    assert result["country"] == "United States"
    assert result["currency"] == "USD"
    assert result["ticker"] == "AAPL"
    assert result["decision"] in {"BUY", "WAIT", "HOLD", "SELL"}

