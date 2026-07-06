from __future__ import annotations

from dataclasses import dataclass

from trading_bot.app.domain import IndicatorSet, NewsSignal, SignalAction


@dataclass(frozen=True)
class AIAnalysis:
    sentiment_label: str
    sentiment_score: int
    confidence: float
    reasoning: str
    key_risks: list[str]
    key_opportunities: list[str]
    recommendation: SignalAction


class AIAnalysisService:
    def analyze(
        self,
        news: NewsSignal | None,
        indicators: IndicatorSet | None,
        market_trend: str,
        risk_score: float,
        sector_performance: float = 0.0,
    ) -> AIAnalysis:
        if news is None or indicators is None:
            return AIAnalysis(
                sentiment_label="Neutral",
                sentiment_score=0,
                confidence=0.0,
                reasoning="Insufficient news or technical data.",
                key_risks=["Missing required input data"],
                key_opportunities=[],
                recommendation=SignalAction.WAIT,
            )

        score = news.score
        if score >= 60:
            label = "Very Bullish"
        elif score >= 20:
            label = "Bullish"
        elif score <= -60:
            label = "Very Bearish"
        elif score <= -20:
            label = "Bearish"
        else:
            label = "Neutral"

        risks: list[str] = []
        opportunities: list[str] = []
        if indicators.rsi >= 70:
            risks.append("RSI is overbought")
        if indicators.current_price < indicators.vwap:
            risks.append("Price is below VWAP")
        if indicators.trend == "positive":
            opportunities.append("Positive moving-average and MACD trend")
        if news.score > 20:
            opportunities.append("Constructive news sentiment")

        confidence = min(1.0, (news.confidence + risk_score + (0.7 if market_trend == "positive" else 0.35)) / 3)
        recommendation = SignalAction.WAIT
        if score >= 25 and indicators.trend == "positive" and risk_score >= 0.5 and indicators.rsi < 70:
            recommendation = SignalAction.BUY
        elif score <= -60:
            recommendation = SignalAction.SELL
        elif risks:
            recommendation = SignalAction.HOLD

        return AIAnalysis(
            sentiment_label=label,
            sentiment_score=score,
            confidence=confidence,
            reasoning=(
                f"News score {score}, trend {indicators.trend}, RSI {indicators.rsi:.1f}, "
                f"risk score {risk_score:.2f}, sector performance {sector_performance:.2%}."
            ),
            key_risks=risks,
            key_opportunities=opportunities,
            recommendation=recommendation,
        )

