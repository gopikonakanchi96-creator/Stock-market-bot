from trading_bot.app.domain import IndicatorSet, Instrument, NewsSignal
from trading_bot.config.settings import load_settings
from trading_bot.risk.manager import PortfolioRiskManager
from trading_bot.strategy.signal_engine import AISignalEngine


def indicator(trend: str = "positive", rsi: float = 55) -> IndicatorSet:
    return IndicatorSet(
        current_price=100,
        previous_close=98,
        volume=2_000_000,
        average_volume=1_000_000,
        sma_fast=101,
        sma_slow=99,
        rsi=rsi,
        macd=2,
        macd_signal=1,
        vwap=99,
        atr=3,
        volatility=0.02,
        trend=trend,
    )


def news(score: int = 70, confidence: float = 0.8) -> NewsSignal:
    return NewsSignal("Very Positive", score, confidence, 15, 0.8, ["strong growth"])


def test_signal_requires_news_and_price_confirmation():
    settings = load_settings("config.yaml")
    engine = AISignalEngine(settings.strategy)

    decision = engine.decide(indicator(trend="negative"), news(), 0.8, market_open=True, already_held=False)

    assert decision.action.value == "WAIT"
    assert decision.explanation == "Trend confirmation failed"


def test_low_ai_confidence_blocks_trade():
    settings = load_settings("config.yaml")
    engine = AISignalEngine(settings.strategy)

    decision = engine.decide(indicator(), news(confidence=0.1), 0.8, market_open=True, already_held=False)

    assert decision.action.value == "WAIT"
    assert decision.explanation == "AI news confidence is too low"


def test_risk_manager_sizes_and_limits_trade(monkeypatch):
    monkeypatch.setenv("EMERGENCY_STOP", "false")
    settings = load_settings("config.yaml")
    risk = PortfolioRiskManager(settings.risk)
    instrument = Instrument("AAPL", "AAPL", "US", "United States", "NASDAQ", "USD")

    decision = risk.validate_entry(instrument, price=100, equity_native=100_000, positions={}, trades_today=0, atr=2)

    assert decision.allowed
    assert decision.quantity > 0
