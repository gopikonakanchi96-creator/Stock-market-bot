from stock_trading_bot.config import StrategyConfig
from stock_trading_bot.models import NewsSentiment, TechnicalIndicators
from stock_trading_bot.strategy.signal_engine import SignalEngine


def strategy_config() -> StrategyConfig:
    return StrategyConfig(
        sentiment_buy_threshold=25,
        sentiment_sell_threshold=-60,
        max_rsi_for_buy=70,
        fast_ma_window=10,
        slow_ma_window=30,
        rsi_window=14,
        volume_average_window=20,
        min_news_confidence=0.40,
    )


def indicators(trend: str = "positive", volume: int = 2_000_000, rsi: float = 55) -> TechnicalIndicators:
    return TechnicalIndicators(
        symbol="AAPL",
        current_price=100,
        previous_close=98,
        daily_change_pct=0.02,
        volume=volume,
        average_volume=1_000_000,
        sma_fast=101,
        sma_slow=99,
        rsi=rsi,
        trend=trend,
    )


def sentiment(score: int = 50, confidence: float = 0.8) -> NewsSentiment:
    return NewsSentiment("AAPL", "Positive", score, confidence, ["Strong growth"])


def test_buy_requires_price_confirmation_not_news_alone():
    engine = SignalEngine(strategy_config())

    decision = engine.evaluate_buy("AAPL", indicators(trend="negative"), sentiment(), {})

    assert not decision.should_trade
    assert decision.reason == "Price trend is not positive"


def test_buy_allowed_when_all_conditions_pass():
    engine = SignalEngine(strategy_config())

    decision = engine.evaluate_buy("AAPL", indicators(), sentiment(), {})

    assert decision.should_trade
    assert decision.action == "buy"


def test_uncertain_news_blocks_trade():
    engine = SignalEngine(strategy_config())

    decision = engine.evaluate_buy("AAPL", indicators(), sentiment(score=80, confidence=0.1), {})

    assert not decision.should_trade
    assert decision.reason == "News sentiment confidence too low"
