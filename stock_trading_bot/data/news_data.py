from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from stock_trading_bot.models import NewsSentiment

logger = logging.getLogger(__name__)

POSITIVE_WORDS = {"beat", "growth", "record", "upgrade", "strong", "profit", "surge", "wins", "positive"}
NEGATIVE_WORDS = {"miss", "drop", "downgrade", "weak", "loss", "lawsuit", "probe", "falls", "negative"}


def score_to_label(score: int) -> str:
    if score >= 60:
        return "Very positive"
    if score >= 20:
        return "Positive"
    if score <= -60:
        return "Very negative"
    if score <= -20:
        return "Negative"
    return "Neutral"


def analyze_headlines(symbol: str, headlines: list[str]) -> NewsSentiment:
    if not headlines:
        return NewsSentiment(symbol, "Neutral", 0, 0.0, [])
    text = " ".join(headlines)
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        compound = SentimentIntensityAnalyzer().polarity_scores(text)["compound"]
        score = int(round(compound * 100))
        confidence = min(1.0, abs(compound) + 0.25)
    except ImportError:
        words = [word.strip(".,:;!?()[]").lower() for word in text.split()]
        pos = sum(word in POSITIVE_WORDS for word in words)
        neg = sum(word in NEGATIVE_WORDS for word in words)
        total = max(pos + neg, 1)
        score = int(round(((pos - neg) / total) * 100))
        confidence = min(1.0, total / 4)
    return NewsSentiment(symbol, score_to_label(score), score, confidence, headlines)


class AlpacaNewsData:
    def fetch_headlines(self, symbol: str, limit: int = 10) -> list[str]:
        try:
            from alpaca.data.historical.news import NewsClient
            from alpaca.data.requests import NewsRequest
            import os
        except ImportError as exc:
            raise RuntimeError("alpaca-py is required for Alpaca news data") from exc

        client = NewsClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"))
        request = NewsRequest(
            symbols=symbol,
            start=datetime.now(timezone.utc) - timedelta(days=3),
            end=datetime.now(timezone.utc),
            limit=limit,
        )
        news = client.get_news(request)
        return [item.headline for item in news.news if getattr(item, "headline", None)]

    def get_sentiment(self, symbol: str) -> NewsSentiment | None:
        try:
            return analyze_headlines(symbol, self.fetch_headlines(symbol))
        except Exception:
            logger.exception("Failed to fetch news for %s", symbol)
            return None


class MockNewsData:
    def get_sentiment(self, symbol: str) -> NewsSentiment:
        headlines = [
            f"{symbol} posts strong growth and analyst upgrade after earnings beat",
            f"{symbol} volume surges as investors react to positive guidance",
        ]
        return analyze_headlines(symbol, headlines)

