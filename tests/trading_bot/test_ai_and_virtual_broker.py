from trading_bot.ai.service import AIAnalysisService
from trading_bot.app.domain import IndicatorSet, Instrument, NewsSignal, OrderRequest, OrderSide, SignalAction, StrategyDecision
from trading_bot.paper_broker import VirtualBroker


def test_ai_analysis_recommends_buy_without_executing_trade():
    indicators = IndicatorSet(100, 98, 2_000_000, 1_000_000, 101, 99, 55, 2, 1, 99, 2, 0.02, "positive")
    news = NewsSignal("Very Positive", 80, 0.9, 10, 0.9, ["strong growth"])

    result = AIAnalysisService().analyze(news, indicators, "positive", risk_score=0.8)

    assert result.recommendation == SignalAction.BUY
    assert result.sentiment_label == "Very Bullish"


def test_virtual_broker_simulates_cash_position_and_trade_history():
    broker = VirtualBroker(starting_balances={"USD": 10_000})
    instrument = Instrument("AAPL", "Apple", "US", "United States", "NASDAQ", "USD")
    decision = StrategyDecision(SignalAction.BUY, 0.8, "test", 80, 0.8)
    request = OrderRequest(instrument, OrderSide.BUY, 10, 100, "test buy", decision)

    result = broker.submit_order(request)

    assert result.accepted
    assert "AAPL" in broker.positions
    assert broker.cash["USD"] < 10_000
    assert len(broker.trade_history) == 1

