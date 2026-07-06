from __future__ import annotations

from trading_bot.app.domain import IndicatorSet, NewsSignal, Position, SignalAction, StrategyDecision
from trading_bot.config.settings import StrategySettings


class AISignalEngine:
    def __init__(self, settings: StrategySettings) -> None:
        self.settings = settings

    def decide(
        self,
        indicators: IndicatorSet | None,
        news: NewsSignal | None,
        risk_score: float,
        market_open: bool,
        already_held: bool,
        trading_halted: bool = False,
    ) -> StrategyDecision:
        if not market_open:
            return StrategyDecision(SignalAction.WAIT, 0.0, "Market is closed", news.score if news else 0, risk_score)
        if trading_halted:
            return StrategyDecision(SignalAction.WAIT, 0.0, "Trading is halted", news.score if news else 0, risk_score)
        if indicators is None:
            return StrategyDecision(SignalAction.WAIT, 0.0, "Required market data unavailable", news.score if news else 0, risk_score)
        if news is None or news.confidence < self.settings.min_ai_confidence:
            return StrategyDecision(SignalAction.WAIT, 0.0, "AI news confidence is too low", news.score if news else 0, risk_score)
        if already_held:
            return StrategyDecision(SignalAction.HOLD, 0.45, "Position already held", news.score, risk_score)
        if news.score < self.settings.min_news_score:
            return StrategyDecision(SignalAction.WAIT, 0.30, "News score below threshold", news.score, risk_score)
        if indicators.trend != "positive":
            return StrategyDecision(SignalAction.WAIT, 0.35, "Trend confirmation failed", news.score, risk_score)
        if not indicators.volume_confirmed:
            return StrategyDecision(SignalAction.WAIT, 0.35, "Volume confirmation failed", news.score, risk_score)
        if indicators.rsi >= self.settings.max_rsi_for_buy:
            return StrategyDecision(SignalAction.WAIT, 0.40, "RSI is overbought", news.score, risk_score)
        if risk_score < self.settings.min_risk_score:
            return StrategyDecision(SignalAction.WAIT, 0.35, "Risk score below threshold", news.score, risk_score)
        confidence = min(0.95, (news.confidence + risk_score + 0.75) / 3)
        return StrategyDecision(
            SignalAction.BUY,
            confidence,
            "BUY: sentiment, trend, volume, RSI, MACD, and risk filters passed",
            news.score,
            risk_score,
            {"trend": indicators.trend, "rsi": indicators.rsi, "macd": indicators.macd},
        )

    def decide_exit(
        self,
        position: Position,
        news: NewsSignal | None,
        emergency_stop: bool = False,
        portfolio_risk_exceeded: bool = False,
    ) -> StrategyDecision:
        news_score = news.score if news else 0
        if emergency_stop:
            return StrategyDecision(SignalAction.SELL, 1.0, "Emergency stop activated", news_score, 0.0)
        if position.current_price <= position.stop_loss:
            return StrategyDecision(SignalAction.SELL, 1.0, "Stop loss reached", news_score, 0.0)
        if position.current_price <= position.profit_lock:
            return StrategyDecision(SignalAction.SELL, 1.0, "Dynamic profit lock reached", news_score, 0.0)
        if news and news.score <= -60 and news.confidence >= self.settings.min_ai_confidence:
            return StrategyDecision(SignalAction.SELL, news.confidence, "News turned strongly negative", news_score, 0.0)
        if portfolio_risk_exceeded:
            return StrategyDecision(SignalAction.SELL, 0.9, "Portfolio risk exceeded", news_score, 0.0)
        return StrategyDecision(SignalAction.HOLD, 0.5, "No sell rule triggered", news_score, 0.0)

