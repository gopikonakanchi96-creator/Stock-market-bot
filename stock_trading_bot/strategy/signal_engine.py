from __future__ import annotations

from stock_trading_bot.config import StrategyConfig
from stock_trading_bot.models import NewsSentiment, Position, SignalDecision, TechnicalIndicators


class SignalEngine:
    def __init__(self, config: StrategyConfig) -> None:
        self.config = config

    def evaluate_buy(
        self,
        symbol: str,
        indicators: TechnicalIndicators | None,
        sentiment: NewsSentiment | None,
        positions: dict[str, Position],
    ) -> SignalDecision:
        if indicators is None:
            return SignalDecision(symbol, "skip", False, "Missing market data", None, None)
        if sentiment is None:
            return SignalDecision(symbol, "skip", False, "Missing news sentiment", None, indicators)
        if sentiment.confidence < self.config.min_news_confidence:
            return SignalDecision(symbol, "skip", False, "News sentiment confidence too low", sentiment.score, indicators)
        if sentiment.score < self.config.sentiment_buy_threshold:
            return SignalDecision(symbol, "skip", False, "News score below buy threshold", sentiment.score, indicators)
        if indicators.trend != "positive":
            return SignalDecision(symbol, "skip", False, "Price trend is not positive", sentiment.score, indicators)
        if not indicators.volume_above_average:
            return SignalDecision(symbol, "skip", False, "Volume is not above average", sentiment.score, indicators)
        if indicators.rsi >= self.config.max_rsi_for_buy:
            return SignalDecision(symbol, "skip", False, "RSI is too overbought", sentiment.score, indicators)
        if symbol in positions:
            return SignalDecision(symbol, "skip", False, "Position already held", sentiment.score, indicators)

        return SignalDecision(
            symbol=symbol,
            action="buy",
            should_trade=True,
            reason=(
                f"Buy signal: sentiment={sentiment.score}, trend={indicators.trend}, "
                f"volume={indicators.volume}>{indicators.average_volume:.0f}, rsi={indicators.rsi:.1f}"
            ),
            news_score=sentiment.score,
            indicators=indicators,
        )

    def evaluate_sell(
        self,
        position: Position,
        sentiment: NewsSentiment | None,
        exposure_too_high: bool = False,
        exposure_reason: str = "",
    ) -> SignalDecision:
        if position.current_price <= position.stop_lock_price:
            return SignalDecision(
                position.symbol,
                "sell",
                True,
                f"Price hit stop/profit lock at {position.stop_lock_price:.2f}",
                sentiment.score if sentiment else None,
                None,
            )
        if sentiment and sentiment.score <= self.config.sentiment_sell_threshold:
            return SignalDecision(
                position.symbol,
                "sell",
                True,
                f"News turned strongly negative: {sentiment.score}",
                sentiment.score,
                None,
            )
        if exposure_too_high:
            return SignalDecision(
                position.symbol,
                "sell",
                True,
                f"Risk manager exit: {exposure_reason}",
                sentiment.score if sentiment else None,
                None,
            )
        return SignalDecision(
            position.symbol,
            "hold",
            False,
            "No sell condition met",
            sentiment.score if sentiment else None,
            None,
        )

