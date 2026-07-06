from __future__ import annotations

from datetime import datetime, timezone

from trading_bot.app.domain import NewsSignal
from trading_bot.news.providers import NewsArticle, NewsProvider, default_news_providers


def sentiment_label(score: int) -> str:
    if score >= 60:
        return "Very Positive"
    if score >= 20:
        return "Positive"
    if score <= -60:
        return "Very Negative"
    if score <= -20:
        return "Negative"
    return "Neutral"


class AINewsService:
    def __init__(self, providers: list[NewsProvider] | None = None) -> None:
        self.providers = providers or default_news_providers()

    def collect_articles(self, symbol: str | None = None, country: str | None = None) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        for provider in self.providers:
            try:
                articles.extend(provider.collect(symbol=symbol, country=country))
            except Exception:
                continue
        seen: set[str] = set()
        deduped: list[NewsArticle] = []
        for article in sorted(articles, key=lambda item: (item.reliability, item.published_at), reverse=True):
            key = article.title.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(article)
        return deduped

    def fetch_headlines(self, symbol: str, market_code: str) -> list[str]:
        articles = self.collect_articles(symbol=symbol, country=market_code)
        return [article.title for article in articles]

    def analyze(self, symbol: str, market_code: str) -> NewsSignal:
        articles = self.collect_articles(symbol=symbol, country=market_code)
        headlines = [article.title for article in articles]
        text = " ".join(headlines).lower()
        positive = sum(word in text for word in ["strong", "growth", "improved", "healthy", "positive"])
        negative = sum(word in text for word in ["weak", "loss", "probe", "downgrade", "negative"])
        total = max(positive + negative, 1)
        score = int(((positive - negative) / total) * 100)
        freshness = 9999.0
        reliability = 0.0
        if articles:
            newest = max(article.published_at for article in articles)
            freshness = (datetime.now(timezone.utc) - newest).total_seconds() / 60
            reliability = sum(article.reliability for article in articles) / len(articles)
        return NewsSignal(
            label=sentiment_label(score),
            score=score,
            confidence=min(1.0, 0.25 + total * 0.10 + reliability * 0.35),
            freshness_minutes=freshness,
            source_reliability=reliability,
            headlines=headlines,
        )
